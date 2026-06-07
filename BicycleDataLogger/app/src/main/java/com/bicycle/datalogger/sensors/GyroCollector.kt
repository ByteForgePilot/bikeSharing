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

class GyroCollector(private val context: Context) : SensorEventListener {

    private val sensorManager =
        context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

    private var writer: Writer? = null
    private val lock = Any()

    val data: SharedFlow<GyroData> = MutableSharedFlow(
        replay = 0,
        extraBufferCapacity = 500,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )

    fun start(outputWriter: Writer) {
        writer = outputWriter

        val supported = gyroscope?.let { gyro ->
            sensorManager.registerListener(this, gyro, 20000)
            Log.i(TAG, "陀螺仪已启动 ~50Hz, 最大量程: ${gyro.maximumRange} rad/s")
            true
        } ?: false

        if (!supported) {
            Log.e(TAG, "陀螺仪不可用")
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        writer = null
        Log.i(TAG, "陀螺仪已停止")
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_GYROSCOPE) return

        val data = GyroData(
            timestampNs = event.timestamp,
            gx = event.values[0],
            gy = event.values[1],
            gz = event.values[2]
        )

        // timestamp_ns, GYRO, , , , , , , , gx, gy, gz
        synchronized(lock) {
            writer?.write("${data.timestampNs},陀螺仪,,,,,,,,${"%.4f".format(data.gx)},${"%.4f".format(data.gy)},${"%.4f".format(data.gz)}\n")
        }
        (this.data as MutableSharedFlow).tryEmit(data)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        Log.d(TAG, "陀螺仪精度: $accuracy")
    }

    companion object {
        private const val TAG = "GyroCollector"
    }
}
