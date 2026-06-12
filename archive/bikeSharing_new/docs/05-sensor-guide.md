# 05 — 传感器使用指南

## 坐标系说明

### 手机坐标系（设备参考系）

```
        +Z (屏幕朝上)
         │
         │    /+Y (顶部)
         │   /
         │  /
         └─●────────── +X (右侧)
          手机平放，屏幕朝上
```

| 轴 | 方向 | 加速度计含义 (m/s²) | 陀螺仪含义 (rad/s) |
|----|------|-------------------|-------------------|
| X | 手机右侧 | 横向加速度 | 绕 X 轴旋转 (pitch) |
| Y | 手机顶部 | 纵向加速度 | 绕 Y 轴旋转 (roll) |
| Z | 屏幕朝上 | 垂直加速度（静止时≈9.81） | 绕 Z 轴旋转 (yaw/偏航) |

### 关键注意

- **陀螺仪 z 轴 = 偏航角速度** — 手机平放时，绕 Z 轴的旋转即为偏航方向变化
- **加速度计 z 轴** — 静止时包含重力分量（约 9.81 m/s²），分析前需要去除重力
- **坐标系不随手机旋转** — 设备坐标系随手机旋转而旋转，非世界坐标系

---

## 手机固定方案（推荐）

### 方案 A：手机支架（最佳）

使用市售自行车手机支架，将手机固定在车把中央。

```
        ┌──────┐
        │ 手机  │  ← 屏幕朝骑手
        └──────┘
     ═══════════════
     车把管 (横管)
```

- **加速度计 X 轴** = 车把左右方向（偏摆敏感轴）
- **加速度计 Z 轴** = 上下方向（重力轴 + 振动轴）
- **陀螺仪 Z 轴** = 车把的偏航旋转（车头不正敏感轴）
- **麦克风** 朝向链条方向（通常在车架右侧下方）

### 方案 B：手机放入口袋（不推荐）

仅限缺少手机支架时的权宜方案，数据质量显著下降。

---

## 各故障传感器要求

### 轮胎偏摆 — 加速度计

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 采样率 | 50 Hz | 20Hz 最低，50Hz 更平滑 |
| 量程 | ±16g | 手机默认，骑行振动不超 ±4g |
| 最少采集时长 | 2 秒 | 算法要求 ≥ `sample_rate * 2` 个样本 |
| 推荐采集时长 | 30 秒+ | 更长数据 → 更稳定的 RMS |
| 敏感轴 | X, Z | 横向 + 垂向 |

**固定要求：**
- 手机必须稳固固定在车把或车架上
- 不能用身体（手臂、口袋）缓冲振动
- 手机壳/支架的软垫会衰减高频振动，优先硬连接

### 链条异响 — 麦克风

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 采样率 | 44100 Hz | CD 音质，覆盖人耳范围 |
| 位深 | 16-bit PCM | 标准 |
| 声道 | 单声道 (Mono) | 节省数据量 |
| 录音品质 | HIGH_QUALITY | expo-av Recording preset |

**固定要求：**
- 麦克风尽量靠近链条（30-50 cm 以内）
- 麦克风不要被衣物遮挡
- 注意风噪：大风天骑行时，链条异响可能被风噪淹没
- 使用海绵防风罩（若有）

### 车头不正 — 陀螺仪

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 采样率 | 50 Hz | 20Hz 最低 |
| 量程 | ±2000 deg/s | 手机默认 |
| 最少采集时长 | 3 秒 | 算法要求 ≥ `sample_rate * 3` 个样本 |
| 推荐采集时长 | 30 秒+ | 仅统计直行片段 |
| 敏感轴 | Z | 偏航角 |

**固定要求：**
- 手机固定在车把中央，屏幕朝上
- 手机顶部朝向骑手前方
- 骑行过程中保持直线行驶（用于采集基准数据）

---

## 骑行数据采集协议

### 骑行流程

```
1. 固定手机 → 2. 开始骑行 → 3. 直线段 (10s+ 预热)
→ 4. 采集段 (30+s 直线) → 5. 停止采集 → 6. 结束骑行
```

### 数据质量检查

采集完成后进行以下检查，不合格应提示用户重试：

| 检查项 | 条件 | 处理 |
|--------|------|------|
| 时间戳连续性 | 相邻样本间隔 < 2× 标称间隔 | 超过视为丢帧，标记 gap |
| 加速度幅值检查 | max(|a|) < 16g | 超过则传感器饱和 |
| 音频静音检测 | RMS > 环境噪声本底 | 低于视为无有效信号 |
| 陀螺仪零偏 | 静止时 z 轴输出 ≈ 0 | 偏移 > 1°/s 需校准 |

---

## expo-sensors 配置

移动端使用 `expo-sensors` 库访问原生传感器。

### 加速度计

```typescript
import { Accelerometer } from 'expo-sensors';

// 设置采样间隔 (毫秒)
Accelerometer.setUpdateInterval(50); // 20 Hz (1000/50 = 20)

// 开始监听
const subscription = Accelerometer.addListener(data => {
  console.log(data.x, data.y, data.z); // m/s²
});

// 停止监听
subscription.remove();
```

### 陀螺仪

```typescript
import { Gyroscope } from 'expo-sensors';

Gyroscope.setUpdateInterval(50); // 20 Hz

const subscription = Gyroscope.addListener(data => {
  console.log(data.x, data.y, data.z); // rad/s
});

subscription.remove();
```

### 麦克风（通过 expo-av）

```typescript
import { Audio } from 'expo-av';

await Audio.requestPermissionsAsync();
await Audio.setAudioModeAsync({
  allowsRecordingIOS: true,
  playsInSilentModeIOS: true,
});

const recording = new Audio.Recording();
await recording.prepareToRecordAsync(
  Audio.RecordingOptionsPresets.HIGH_QUALITY
);
await recording.startAsync();
// ... 录音中 ...
await recording.stopAndUnloadAsync();
const uri = recording.getURI();
```

---

## 数据格式

### 传感器样本（单元）

```typescript
interface SensorDataPoint {
  x: number;        // X 轴分量
  y: number;        // Y 轴分量
  z: number;        // Z 轴分量
  timestamp: number; // Unix 时间戳 (秒)
}
```

### 传感器缓冲区

```typescript
interface SensorBuffer {
  accelerometer: SensorDataPoint[];
  gyroscope: SensorDataPoint[];
  sampleCount: number;
}
```

缓冲区每 100 个样本（约 5 秒 @ 20Hz）自动触发 flush，通过回调上传至后端。

### 后端 Pydantic Schema

```python
class SensorSample(BaseModel):
    x: float
    y: float
    z: float
    timestamp: float
```

---

## 机型兼容性

| 平台 | 加速度计 | 陀螺仪 | 麦克风 |
|------|---------|--------|--------|
| iOS 14+ | ✅ 全机型 | ✅ 全机型 | ✅ 全机型 |
| Android 10+ | ✅ 全机型 | ⚠️ 部分低端机无陀螺仪 | ✅ 全机型 |

**已知问题：**
- 部分 Android 机型的陀螺仪在高温下零偏漂移严重
- iOS 的 `expo-sensors` 采样间隔下限为 ~16ms (约 60Hz)
- Android 的采样间隔取决于硬件和系统负载，可能不准时

### 传感器可用性检查

```typescript
import { checkSensorsAvailable } from '../services/sensors';

const { accelerometer, gyroscope } = await checkSensorsAvailable();
if (!gyroscope) {
  Alert.alert('您的手机不支持陀螺仪，车头不正检测将不可用');
}
```
