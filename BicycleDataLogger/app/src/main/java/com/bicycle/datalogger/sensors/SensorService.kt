package com.bicycle.datalogger.sensors

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Environment
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.bicycle.datalogger.MainActivity
import kotlinx.coroutines.*
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File
import java.io.FileWriter
import java.io.Writer
import java.text.SimpleDateFormat
import java.util.*

class SensorService : Service() {

    private lateinit var accelCollector: AccelCollector
    private lateinit var gpsCollector: GpsCollector
    private lateinit var gyroCollector: GyroCollector
    private lateinit var audioCollector: AudioCollector

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var collectionJob: Job? = null
    private var timerJob: Job? = null
    private var wakeLock: PowerManager.WakeLock? = null

    private lateinit var sessionDir: File
    private var combinedWriter: Writer? = null

    companion object {
        private const val TAG = "SensorService"
        const val ACTION_START = "com.bicycle.datalogger.START"
        const val ACTION_STOP = "com.bicycle.datalogger.STOP"
        const val NOTIFICATION_ID = 1001
        const val CHANNEL_ID = "sensor_collection"

        private val _sessionState = MutableStateFlow<SessionState>(SessionState.Idle)
        val sessionState: StateFlow<SessionState> = _sessionState
        val isRunning = MutableStateFlow(false)
        val elapsedMs = MutableStateFlow(0L)
        val sessionPath = MutableStateFlow("")
        val debugLog = MutableStateFlow("")
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        accelCollector = AccelCollector(this)
        gpsCollector = GpsCollector(this)
        gyroCollector = GyroCollector(this)
        audioCollector = AudioCollector()
        // 整个生命周期只进入一次前台，后续只更新通知内容
        startForeground(NOTIFICATION_ID, buildNotification("就绪"))
        Log.d(TAG, "服务已创建，已进入前台")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        debugLog.value = "[${System.currentTimeMillis() % 100000}] onStartCommand( action=${intent?.action} )"
        when (intent?.action) {
            ACTION_START -> startCollection()
            ACTION_STOP -> pauseCollection()
            else -> debugLog.value = "[${System.currentTimeMillis() % 100000}] 未知action: ${intent?.action}"
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        collectionJob?.cancel()
        timerJob?.cancel()
        accelCollector.stop()
        gpsCollector.stop()
        gyroCollector.stop()
        audioCollector.stop()
        try { combinedWriter?.close() } catch (_: Exception) {}
        releaseWakeLock()
        serviceScope.cancel()
        super.onDestroy()
        Log.d(TAG, "服务已销毁")
    }

    // ========== 开始采集 ==========

    private fun startCollection() {
        debugLog.value = "[${System.currentTimeMillis() % 100000}] startCollection() 进入, isRunning=${isRunning.value}"
        if (isRunning.value) {
            debugLog.value = "[${System.currentTimeMillis() % 100000}] 已在采集中，忽略"
            Log.w(TAG, "已在采集中，忽略重复启动")
            return
        }

        acquireWakeLock()
        isRunning.value = true
        _sessionState.value = SessionState.Collecting
        elapsedMs.value = 0L

        updateNotification("正在采集传感器数据...")
        startTimer()
        debugLog.value = "[${System.currentTimeMillis() % 100000}] 采集已启动, isRunning=true"

        collectionJob = serviceScope.launch {
            try {
                val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
                sessionDir = createSessionDir(timestamp)
                sessionPath.value = sessionDir.absolutePath
                Log.i(TAG, "采集目录: ${sessionDir.absolutePath}")

                val dataFile = File(sessionDir, "传感器数据.txt")
                combinedWriter = FileWriter(dataFile)
                combinedWriter?.write("timestamp_ns,传感器类型,ax(m/s²),ay(m/s²),az(m/s²),纬度,经度,速度(m/s),航向角(°),gx(rad/s),gy(rad/s),gz(rad/s)\n")

                val dataJobs = listOf(
                    launch { startAccelWriter() },
                    launch { startGpsWriter() },
                    launch { startGyroWriter() },
                    launch { startAudioWriters() }
                )

                Log.i(TAG, "所有传感器已启动")
                dataJobs.forEach { it.join() }
                Log.i(TAG, "所有采集器已停止")

            } catch (e: CancellationException) {
                Log.i(TAG, "采集被用户暂停")
            } catch (e: Exception) {
                Log.e(TAG, "采集出错: ${e.message}", e)
                _sessionState.value = SessionState.Error(e.message ?: "未知错误")
            } finally {
                withContext(NonCancellable + Dispatchers.Main) { cleanupSession() }
            }
        }
    }

    // ========== 暂停采集 ==========

    private fun pauseCollection() {
        debugLog.value = "[${System.currentTimeMillis() % 100000}] pauseCollection() 收到暂停请求"
        Log.i(TAG, "收到暂停请求")
        collectionJob?.cancel()
        timerJob?.cancel()
    }

    private fun cleanupSession() {
        timerJob?.cancel()
        try { accelCollector.stop() } catch (_: Exception) {}
        try { gpsCollector.stop() } catch (_: Exception) {}
        try { gyroCollector.stop() } catch (_: Exception) {}
        try { audioCollector.stop() } catch (_: Exception) {}

        try {
            combinedWriter?.flush()
            combinedWriter?.close()
        } catch (e: Exception) {
            Log.e(TAG, "关闭文件出错: ${e.message}")
        }
        combinedWriter = null

        releaseWakeLock()

        isRunning.value = false
        elapsedMs.value = 0L
        _sessionState.value = SessionState.Idle
        val savedPath = sessionPath.value
        sessionPath.value = ""

        updateNotification("就绪")
        debugLog.value = "[${System.currentTimeMillis() % 100000}] cleanupSession() 完成, isRunning=${isRunning.value}, 数据: $savedPath"
        Log.i(TAG, "采集已暂停，数据已保存至: $savedPath")
    }

    // ========== 辅助方法 ==========

    private fun createSessionDir(timestamp: String): File {
        return try {
            val docDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS)
            val dir = File(docDir, "自行车数据/$timestamp")
            dir.mkdirs()
            if (dir.exists() && dir.canWrite()) dir else throw Exception("无法创建或写入目录")
        } catch (e: Exception) {
            Log.w(TAG, "公共目录不可写，回退到应用目录: ${e.message}")
            val fallback = File(getExternalFilesDir(null) ?: filesDir, "session_$timestamp")
            fallback.mkdirs()
            fallback
        }
    }

    private fun startTimer() {
        val startTime = System.currentTimeMillis()
        timerJob?.cancel()
        timerJob = serviceScope.launch {
            while (isActive) {
                elapsedMs.value = System.currentTimeMillis() - startTime
                delay(200)
            }
        }
    }

    private suspend fun startAccelWriter() {
        val writer = combinedWriter ?: return
        withContext(Dispatchers.Main) { accelCollector.start(writer) }
        try { delay(Long.MAX_VALUE) } catch (_: CancellationException) {}
        withContext(Dispatchers.Main) { accelCollector.stop() }
    }

    private suspend fun startGpsWriter() {
        val writer = combinedWriter ?: return
        withContext(Dispatchers.Main) { gpsCollector.start(writer) }
        try { delay(Long.MAX_VALUE) } catch (_: CancellationException) {}
        withContext(Dispatchers.Main) { gpsCollector.stop() }
    }

    private suspend fun startGyroWriter() {
        val writer = combinedWriter ?: return
        withContext(Dispatchers.Main) { gyroCollector.start(writer) }
        try { delay(Long.MAX_VALUE) } catch (_: CancellationException) {}
        withContext(Dispatchers.Main) { gyroCollector.stop() }
    }

    private suspend fun startAudioWriters() {
        val pcmFile = File(sessionDir, "音频.pcm")
        val metaFile = File(sessionDir, "音频_时间戳.csv")
        val metaWriter = FileWriter(metaFile)
        try {
            audioCollector.start(pcmFile, metaWriter)
            try { delay(Long.MAX_VALUE) } catch (_: CancellationException) {}
            audioCollector.stop()
        } finally {
            try { metaWriter.close() } catch (_: Exception) {}
        }
    }

    private fun acquireWakeLock() {
        releaseWakeLock()
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "BicycleDataLogger:WakeLock"
        )
        wakeLock?.acquire(10 * 60 * 1000L)
    }

    private fun releaseWakeLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun buildNotification(text: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("自行车数据采集")
        .setContentText(text)
        .setSmallIcon(android.R.drawable.ic_menu_compass)
        .setContentIntent(
            PendingIntent.getActivity(
                this, 0,
                Intent(this, MainActivity::class.java),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        )
        .setOngoing(true)
        .build()

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "传感器采集",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "传感器数据采集进行中的通知"
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }
}
