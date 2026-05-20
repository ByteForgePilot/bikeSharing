package com.bicycle.datalogger.sensors

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import java.io.Writer

@SuppressLint("MissingPermission")
class GpsCollector(private val context: Context) : LocationListener {

    private val locationManager =
        context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

    private var writer: Writer? = null
    private val lock = Any()

    val data: SharedFlow<GpsData> = MutableSharedFlow(
        replay = 0,
        extraBufferCapacity = 10,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )

    fun start(outputWriter: Writer) {
        writer = outputWriter

        try {
            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1000L,
                0f,
                this
            )
            Log.i(TAG, "GPS已启动 1Hz")
        } catch (e: SecurityException) {
            Log.e(TAG, "GPS权限被拒绝: ${e.message}")
        }
    }

    fun stop() {
        locationManager.removeUpdates(this)
        writer = null
        Log.i(TAG, "GPS已停止")
    }

    override fun onLocationChanged(location: Location) {
        val elapsedNs = SystemClock.elapsedRealtimeNanos()

        val speedStr = if (location.hasSpeed()) "%.4f".format(location.speed) else ""
        val courseStr = if (location.hasBearing()) "%.4f".format(location.bearing) else ""

        // timestamp_ns, GPS, , , , lat, lon, speed, course, , , ,
        synchronized(lock) {
            writer?.write(
                "${elapsedNs},GPS,,,," +
                "${"%.4f".format(location.latitude)},${"%.4f".format(location.longitude)}," +
                "$speedStr,$courseStr,,,\n"
            )
        }

        val data = GpsData(
            timestampNs = elapsedNs,
            latitude = location.latitude,
            longitude = location.longitude,
            speedMps = if (location.hasSpeed()) location.speed else Float.NaN,
            courseDeg = if (location.hasBearing()) location.bearing else Float.NaN,
            hasSpeed = location.hasSpeed(),
            hasCourse = location.hasBearing()
        )

        (this.data as MutableSharedFlow).tryEmit(data)
    }

    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    override fun onProviderEnabled(provider: String) {
        Log.d(TAG, "GPS已启用: $provider")
    }
    override fun onProviderDisabled(provider: String) {
        Log.w(TAG, "GPS已禁用: $provider")
    }

    companion object {
        private const val TAG = "GpsCollector"
    }
}
