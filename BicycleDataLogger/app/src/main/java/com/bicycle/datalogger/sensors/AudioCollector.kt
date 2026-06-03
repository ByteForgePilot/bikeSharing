package com.bicycle.datalogger.sensors

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

class AudioCollector {

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var pcmFile: RandomAccessFile? = null
    private var metaWriter: java.io.Writer? = null

    val metaData: SharedFlow<AudioMeta> = MutableSharedFlow(replay = 0, extraBufferCapacity = 100)

    suspend fun start(pcmOutput: File, metaOutput: java.io.Writer) = withContext(Dispatchers.IO) {
        metaWriter = metaOutput
        metaWriter?.write("timestamp_ns,累计采样数\n")

        val sampleRate = 8000
        val channelConfig = AudioFormat.CHANNEL_IN_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT

        val minBufSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
        val bufferSize = minBufSize * 2

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            channelConfig,
            audioFormat,
            bufferSize
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            audioRecord?.release()
            audioRecord = null
            throw IllegalStateException("AudioRecord 初始化失败，麦克风可能被占用")
        }

        pcmFile = RandomAccessFile(pcmOutput, "rw")
        pcmFile?.setLength(0)

        audioRecord?.startRecording()
        isRecording = true

        Log.i(TAG, "音频录制已启动: 8kHz, 16-bit PCM, 缓冲区=${bufferSize}B")

        val buffer = ShortArray(minBufSize / 2)
        val byteBuffer = ByteBuffer.allocate(minBufSize).order(ByteOrder.LITTLE_ENDIAN)
        var totalSamples = 0L

        while (isRecording) {
            val samplesRead = audioRecord?.read(buffer, 0, buffer.size) ?: break
            if (samplesRead <= 0) continue

            byteBuffer.clear()
            for (i in 0 until samplesRead) {
                byteBuffer.putShort(buffer[i])
            }
            pcmFile?.write(byteBuffer.array(), 0, samplesRead * 2)

            totalSamples += samplesRead

            val meta = AudioMeta(
                timestampNs = SystemClock.elapsedRealtimeNanos(),
                sampleCount = samplesRead
            )
            metaWriter?.write("${meta.timestampNs},${totalSamples}\n")
            (metaData as MutableSharedFlow).tryEmit(meta)
        }
    }

    fun stop() {
        synchronized(this) {
            if (audioRecord == null && pcmFile == null && metaWriter == null) return
            isRecording = false
            audioRecord?.apply {
                stop()
                release()
            }
            audioRecord = null
            try { pcmFile?.close() } catch (_: Exception) {}
            pcmFile = null
            try { metaWriter?.flush() } catch (_: Exception) {}
            try { metaWriter?.close() } catch (_: Exception) {}
            metaWriter = null
            Log.i(TAG, "音频录制已停止")
        }
    }

    companion object {
        private const val TAG = "AudioCollector"
    }
}
