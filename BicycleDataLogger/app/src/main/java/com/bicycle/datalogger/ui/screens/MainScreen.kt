package com.bicycle.datalogger.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bicycle.datalogger.sensors.SessionState
import kotlinx.coroutines.flow.StateFlow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    isRunning: StateFlow<Boolean>,
    sessionState: StateFlow<SessionState>,
    elapsedMs: StateFlow<Long>,
    sessionPath: StateFlow<String>,
    onStart: () -> Unit,
    onStop: () -> Unit,
    debugLog: StateFlow<String>? = null
) {
    val running by isRunning.collectAsState()
    val state by sessionState.collectAsState()
    val elapsed by elapsedMs.collectAsState()
    val path by sessionPath.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("自行车数据采集") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 状态卡片
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = when (state) {
                        is SessionState.Idle -> MaterialTheme.colorScheme.surface
                        is SessionState.Collecting -> MaterialTheme.colorScheme.primaryContainer
                        is SessionState.Error -> MaterialTheme.colorScheme.errorContainer
                    }
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = when (state) {
                            is SessionState.Idle -> "就绪"
                            is SessionState.Collecting -> "正在采集..."
                            is SessionState.Error -> "错误: ${(state as SessionState.Error).message}"
                        },
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )

                    // 计时器
                    if (running) {
                        Spacer(modifier = Modifier.height(12.dp))
                        val seconds = elapsed / 1000
                        val minutes = seconds / 60
                        val hours = minutes / 60
                        val timeText = when {
                            hours > 0 -> "%d时%02d分%02d秒".format(hours, minutes % 60, seconds % 60)
                            else -> "%02d分%02d秒".format(minutes, seconds % 60)
                        }
                        Text(
                            text = "已采集: $timeText",
                            fontSize = 24.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 主控制按钮
            Button(
                onClick = { if (running) onStop() else onStart() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (running)
                        MaterialTheme.colorScheme.error
                    else
                        MaterialTheme.colorScheme.primary
                )
            ) {
                Text(
                    text = if (running) "暂停采集" else "再次开始",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 传感器状态
            SensorStatusCard(running = running)

            Spacer(modifier = Modifier.height(16.dp))

            // 数据输出说明
            SensorParametersCard()

            // 保存路径
            if (path.isNotEmpty()) {
                Spacer(modifier = Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.secondaryContainer
                    )
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "保存位置",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = path,
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSecondaryContainer
                        )
                    }
                }
            }

            // 调试日志
            val log by (debugLog ?: kotlinx.coroutines.flow.MutableStateFlow("")).collectAsState()
            if (log.isNotEmpty()) {
                Spacer(modifier = Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("调试信息", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(log, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

@Composable
private fun SensorStatusCard(running: Boolean) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "传感器状态",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(8.dp))

            SensorRow("加速度计", "100 Hz", "三轴 (Z=垂直方向)", running)
            SensorRow("GPS", "1 Hz", "速度 + 航向角", running)
            SensorRow("陀螺仪", "50 Hz", "偏航角速度 (车把)", running)
            SensorRow("麦克风", "8 kHz", "16-bit PCM 单声道", running)
        }
    }
}

@Composable
private fun SensorRow(
    name: String,
    rate: String,
    detail: String,
    active: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = name, modifier = Modifier.weight(1f))
        Text(
            text = rate,
            modifier = Modifier.weight(0.5f),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = detail,
            modifier = Modifier.weight(1f),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontSize = 12.sp
        )
        Surface(
            shape = MaterialTheme.shapes.small,
            color = if (active)
                MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
            else
                MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.padding(start = 4.dp)
        ) {
            Text(
                text = if (active) "开" else "—",
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                fontSize = 11.sp,
                color = if (active) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun SensorParametersCard() {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "数据输出",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(8.dp))

            ParamRow("合并数据", "传感器数据.txt  (加速度计+GPS+陀螺仪)")
            ParamRow("音频", "音频.pcm + 音频_时间戳.csv")
            ParamRow("时间戳", "纳秒级 (SystemClock.elapsedRealtimeNanos)")
        }
    }
}

@Composable
private fun ParamRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
    ) {
        Text(
            text = label,
            modifier = Modifier.width(80.dp),
            fontWeight = FontWeight.Medium,
            fontSize = 13.sp
        )
        Text(
            text = value,
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
