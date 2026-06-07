# 06 -- BicycleDataLogger 原生 Android 数据采集

## 概述

BicycleDataLogger 是原生 Android（Kotlin + Jetpack Compose）数据采集 App。通过前台 Service 实现可靠的长时间后台传感器采集，输出 CSV + PCM 文件供后端检测引擎分析。

| 属性 | 值 |
|------|-----|
| 语言 | Kotlin |
| UI 框架 | Jetpack Compose |
| 最低 SDK | 24 (Android 7.0) |
| 编译 SDK | 34 |

## 采集能力

| 传感器 | 采样率 | 格式 | 说明 |
|--------|--------|------|------|
| 加速度计 | 100Hz | CSV 行 | TYPE_ACCELEROMETER，ax/ay/az (m/s^2) |
| 陀螺仪 | ~50Hz | CSV 行 | TYPE_GYROSCOPE，gx/gy/gz (rad/s) |
| GPS | 10Hz | CSV 行 | GPS_PROVIDER + NETWORK_PROVIDER 备用 |
| 音频 | 8kHz | PCM 16-bit LE | AudioRecord 直接写入 音频.pcm |

## 架构

```
MainActivity (Compose UI)
    └─ start/stop → SensorService (Foreground Service)
                        ├─ AccelCollector (SensorManager, 100Hz)  ─┐
                        ├─ GyroCollector (SensorManager, 50Hz)   ──┤
                        ├─ GpsCollector (LocationManager, 10Hz)   ──┼─→ 传感器数据.txt
                        └─ AudioCollector (AudioRecord, 8kHz)     ──┤     (合并 CSV)
                                                                   └─→ 音频.pcm + 音频_时间戳.csv
```

## 数据输出格式

### 传感器数据.txt

CSV 格式，首行为列标题，后续每行一个传感器事件：

```
timestamp_ns,传感器类型,ax(m/s^2),ay(m/s^2),az(m/s^2),纬度,经度,速度(m/s),航向角(°),gx(rad/s),gy(rad/s),gz(rad/s)
123456789,加速度计,0.12,0.05,9.81,,,,,,,,
123456799,陀螺仪,,,,,,,,0.01,0.02,0.03
123456809,GPS,,,39.9042,116.4074,5.2,180.5,,,,
```

列对应关系：

| 列索引 | 内容 | 加速度计 | 陀螺仪 | GPS |
|--------|------|:---:|:---:|:---:|
| 0 | timestamp_ns | ✓ | ✓ | ✓ |
| 1 | 传感器类型 | 加速度计 | 陀螺仪 | GPS |
| 2-4 | ax/ay/az | ✓ | | |
| 5-6 | 纬度/经度 | | | ✓ |
| 7 | 速度 m/s | | | ✓ |
| 8 | 航向角 (°) | | | ✓ |
| 9-11 | gx/gy/gz | | ✓ | |

### 音频.pcm

16-bit 小端序 PCM，单声道，8000Hz。每帧 2 字节。

### 音频_时间戳.csv

```
timestamp_ns,累计采样数
123456000,512
124750000,1024
```

## 构建与安装

用 Android Studio 打开 `BicycleDataLogger/` 目录，Sync Gradle 后构建 APK：

```bash
# 命令行构建
cd BicycleDataLogger
./gradlew assembleDebug
# APK 位于 app/build/outputs/apk/debug/
```

APK 安装到手机后，需要授予位置和麦克风权限。

## 骑行流程

1. App 首页点击"开始采集" → 前台通知显示"正在采集传感器数据..."
2. 骑行过程中，数据持续写入 `Documents/自行车数据/<yyyyMMdd_HHmmss>/`
3. 暂停：通知栏操作或 App 内暂停 → 采集停止，数据已保存
4. 将三文件上传到后端 `POST /api/detection/upload/{ride_id}`

## 关键实现细节

- **前台 Service**：`SensorService` 作为 foreground service 运行，防止系统在后台杀死采集进程
- **WakeLock**：`PARTIAL_WAKE_LOCK` 防止 CPU 休眠，超时 10 分钟
- **合并 CSV**：所有传感器写入同一文件（synchronized），按时间戳自然混合
- **GPS 双源**：GPS_PROVIDER (10Hz) 为主，NETWORK_PROVIDER (5s) 为备用
- **PCM 直接写入**：AudioRecord 读取后直接写 RandomAccessFile，无中间缓冲
