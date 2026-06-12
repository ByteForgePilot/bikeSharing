package com.bicycle.datalogger.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Log
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import java.io.Writer

class AccelCollector(private val context: Context) : SensorEventListener {

    private val sensorManager =
        context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    private var writer: Writer? = null
    private val lock = Any()

    val data: SharedFlow<AccelData> = MutableSharedFlow(
        replay = 0,
        extraBufferCapacity = 500,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )

    fun start(outputWriter: Writer) {
        writer = outputWriter

        val supported = accelerometer?.let { accel ->
            sensorManager.registerListener(this, accel, 10000)
            Log.i(TAG, "加速度计已启动 100Hz, 最大量程: ${accel.maximumRange}")
            true
        } ?: false

        if (!supported) {
            Log.e(TAG, "加速度计不可用")
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        writer = null
        Log.i(TAG, "加速度计已停止")
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_ACCELEROMETER) return

        val data = AccelData(
            timestampNs = event.timestamp,
            ax = event.values[0],
            ay = event.values[1],
            az = event.values[2]
        )

        // 写入合并文件：timestamp_ns, ACCEL, ax, ay, az, , , , , , ,
        synchronized(lock) {
            writer?.write("${data.timestampNs},加速度计,${"%.4f".format(data.ax)},${"%.4f".format(data.ay)},${"%.4f".format(data.az)},,,,,,,\n")
        }
        (this.data as MutableSharedFlow).tryEmit(data)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        Log.d(TAG, "加速度计精度: $accuracy")
    }

    companion object {
        private const val TAG = "AccelCollector"
    }
}
