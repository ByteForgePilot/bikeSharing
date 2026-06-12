package com.bicycle.datalogger.sensors

/**
 * 统一的传感器数据点，包含纳秒级时间戳用于同步。
 */
data class AccelData(
    val timestampNs: Long,
    val ax: Float,  // m/s^2
    val ay: Float,
    val az: Float
)

data class GpsData(
    val timestampNs: Long,
    val latitude: Double,
    val longitude: Double,
    val speedMps: Float,       // m/s
    val courseDeg: Float,      // 航向角 (0-360°)
    val hasSpeed: Boolean,
    val hasCourse: Boolean
)

data class GyroData(
    val timestampNs: Long,
    val gx: Float,  // rad/s around X
    val gy: Float,  // rad/s around Y
    val gz: Float   // rad/s around Z (偏航角速度)
)

data class AudioMeta(
    val timestampNs: Long,
    val sampleCount: Int   // 自上次记录以来的采样数
)

/** 采集会话状态 */
sealed class SessionState {
    data object Idle : SessionState()
    data object Collecting : SessionState()
    data class Error(val message: String) : SessionState()
}
