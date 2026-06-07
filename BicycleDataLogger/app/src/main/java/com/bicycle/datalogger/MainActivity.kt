package com.bicycle.datalogger

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.bicycle.datalogger.sensors.SensorService
import com.bicycle.datalogger.ui.screens.MainScreen
import com.bicycle.datalogger.ui.theme.BicycleTheme

class MainActivity : ComponentActivity() {

    private val criticalPermissions = listOf(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.RECORD_AUDIO,
    )

    private val niceToHavePermissions = buildList {
        add(Manifest.permission.ACCESS_COARSE_LOCATION)
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
            add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private val allPermissions = criticalPermissions + niceToHavePermissions

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        val missingCritical = criticalPermissions.any { grants[it] != true }
        if (missingCritical) {
            Toast.makeText(this, "位置和麦克风权限是采集数据所必需的，请在系统设置中授予", Toast.LENGTH_LONG).show()
            return@registerForActivityResult
        }
        checkManageStorageAndProceed()
    }

    private val manageStorageLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        startCollection()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val crashLog = getSharedPreferences("crash_log", MODE_PRIVATE)
        val lastCrash = crashLog.getString("last_crash", null)

        Thread.setDefaultUncaughtExceptionHandler { _, ex ->
            Log.e("BicycleCrash", "未捕获异常", ex)
            crashLog.edit().putString("last_crash", ex.stackTraceToString()).commit()
            android.os.Process.killProcess(android.os.Process.myPid())
        }

        try {
            setContent {
                BicycleTheme {
                    if (lastCrash != null) {
                        CrashScreen(
                            error = lastCrash,
                            onDismiss = { crashLog.edit().remove("last_crash").commit() }
                        )
                    } else {
                        MainScreen(
                            isRunning = SensorService.isRunning,
                            sessionState = SensorService.sessionState,
                            elapsedMs = SensorService.elapsedMs,
                            sessionPath = SensorService.sessionPath,
                            onStart = { onStartClick() },
                            onStop = { onStopClick() },
                            debugLog = SensorService.debugLog
                        )
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("BicycleCrash", "onCreate异常", e)
            crashLog.edit().putString("last_crash", e.stackTraceToString()).commit()
        }
    }

    private fun onStartClick() {
        Toast.makeText(this, "点击了开始, isRunning=${SensorService.isRunning.value}", Toast.LENGTH_SHORT).show()
        if (SensorService.isRunning.value) {
            Toast.makeText(this, "已在运行中，忽略", Toast.LENGTH_SHORT).show()
            return
        }

        val notGranted = allPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (notGranted.isEmpty()) {
            checkManageStorageAndProceed()
        } else {
            val missingCritical = notGranted.any { it in criticalPermissions }
            if (missingCritical) {
                permissionLauncher.launch(notGranted.toTypedArray())
            } else {
                checkManageStorageAndProceed()
            }
        }
    }

    private fun onStopClick() {
        Toast.makeText(this, "点击了暂停", Toast.LENGTH_SHORT).show()
        sendServiceAction(SensorService.ACTION_STOP)
    }

    private fun checkManageStorageAndProceed() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                try {
                    manageStorageLauncher.launch(
                        Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                            data = Uri.parse("package:$packageName")
                        }
                    )
                } catch (e: ActivityNotFoundException) {
                    Toast.makeText(this, "当前系统不支持全局存储授权，将使用应用私有目录保存数据", Toast.LENGTH_LONG).show()
                    startCollection()
                }
                return
            }
        }
        startCollection()
    }

    private fun startCollection() {
        sendServiceAction(SensorService.ACTION_START)
    }

    private fun sendServiceAction(action: String) {
        val intent = Intent(this, SensorService::class.java).apply {
            this.action = action
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (e: Exception) {
            Log.e("Bicycle", "sendServiceAction($action) 失败", e)
            Toast.makeText(this, "操作失败: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
}

@Composable
private fun CrashScreen(error: String, onDismiss: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(48.dp))
        Text("上次崩溃信息", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
        Spacer(modifier = Modifier.height(16.dp))
        Text(error, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurface)
        Spacer(modifier = Modifier.height(24.dp))
        Button(onClick = onDismiss) { Text("关闭") }
    }
}
