# 06 — 移动端开发指南

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React Native | 0.76.5 | 跨平台移动框架 |
| Expo | 52.0.0 | RN 工具链 + 托管环境 |
| Expo Router | 4.0.0 | 文件系统路由 |
| expo-sensors | 14.0.0 | 加速度计 + 陀螺仪 |
| expo-av | 15.0.0 | 麦克风录音 |
| TypeScript | 5.3.3 | 类型检查 |

---

## 项目初始化

```bash
cd mobile
npm install          # 安装依赖
npx expo start       # 启动开发服务器
```

Expo Go 扫码即可在真机上运行（无需编译原生应用）。

---

## 页面路由架构

基于 Expo Router 的文件系统路由：

```
app/
├── _layout.tsx          # 根布局 (Stack Navigator)
└── (tabs)/
    ├── _layout.tsx       # Tab 导航配置
    ├── index.tsx         # Tab 1: 首页 ("骑行")
    ├── ride.tsx          # Tab 2: 骑行中 ("检测中")
    └── history.tsx       # Tab 3: 历史记录 ("历史")
```

### 根布局 (`_layout.tsx`)

```tsx
// Stack 导航，默认隐藏 header
<Stack>
  <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
</Stack>
```

### Tab 布局 (`(tabs)/_layout.tsx`)

三 Tab 导航，蓝色主题 (`#2563eb`)：

| Tab | 路由 | 标题 | 图标 |
|-----|------|------|------|
| index | `/(tabs)` | "骑行" | `bicycle` (Ionicons) |
| ride | `/(tabs)/ride` | "检测中" | `speedometer` (Ionicons) |
| history | `/(tabs)/history` | "历史" | `time` (Ionicons) |

---

## 页面详解

### 首页 (`index.tsx`)

**功能：** 输入单车编号，开始骑行

**State:**
- `bikeId: string` — 单车编号输入值
- `isRiding: boolean` — 是否骑行中

**交互流程：**
```
1. 用户输入 bike_id (或点击"扫描二维码"→占位提示)
2. 点击"开始骑行"
3. router.push({ pathname: '/(tabs)/ride', params: { bikeId } })
```

**UI 结构：**
```
┌──────────────────────┐
│    🚲 bikeSharing    │
│   共享单车故障检测    │
├──────────────────────┤
│ 单车编号: [______]   │
│ [📷 扫码] [▶ 开始骑行] │
├──────────────────────┤
│ 检测项目:            │
│ 🛞 轮胎偏摆 — 加速度计│
│ 🔗 链条异响 — 麦克风  │
│ 🔧 车头不正 — 陀螺仪  │
└──────────────────────┘
```

---

### 骑行页 (`ride.tsx`)

**功能：** 实时采集传感器数据，模拟故障检测

**State:**
- `isRecording: boolean` — 是否采集中
- `elapsed: number` — 已骑行秒数
- `accelData: {x,y,z} | null` — 最新加速度计读数
- `gyroData: {x,y,z} | null` — 最新陀螺仪读数
- `faultStatus: {wheel, chain, handlebar}` — 故障检测状态（字符串）

**传感器采集：**
```typescript
// 挂载时启动，卸载时清理
useEffect(() => {
  startSensors();
  return () => stopSensors();
}, []);

function startSensors() {
  Accelerometer.setUpdateInterval(50); // 20Hz
  Gyroscope.setUpdateInterval(50);

  accelSub = Accelerometer.addListener(setAccelData);
  gyroSub = Gyroscope.addListener(setGyroData);
  setIsRecording(true);
}
```

**模拟故障检测（用于演示，实际应调用后端 API）：**
```typescript
// 3 秒后: 轮胎和链条显示正常
// 10 秒后: 链条变为异常
useEffect(() => {
  if (elapsed > 10) {
    setFaultStatus(prev => ({ ...prev, chain: "异常" }));
  } else if (elapsed > 3) {
    setFaultStatus({ wheel: "正常", chain: "正常", handlebar: "检测中" });
  }
}, [elapsed]);
```

**UI 结构：**
```
┌──────────────────────┐
│ 单车: BIKE-001  ● 活跃│
│ ⏱ 05:32             │
├──────────────────────┤
│ 📊 传感器数据         │
│ 加速度计 X: +0.12    │
│          Y: +0.05    │
│          Z: +9.81    │
│ 陀螺仪   X: +0.01    │
│          Y: +0.02    │
│          Z: +0.00    │
├──────────────────────┤
│ 🔍 检测状态           │
│ 🛞 轮胎偏摆  ✅ 正常  │
│ 🔗 链条异响  ❌ 异常  │
│ 🔧 车头不正  ⏳ 检测中│
├──────────────────────┤
│   [🔴 结束骑行]       │
└──────────────────────┘
```

---

### 历史页 (`history.tsx`)

**功能：** 展示历史骑行记录与检测结果

**Mock 数据（3 条记录）：**
```typescript
const MOCK_RIDES = [
  { id: 1, bikeId: "BIKE-001", date: "2026-05-12 08:30",
    duration: "12:30", wheel_wobble: "正常",
    chain_noise: "正常", handlebar: "正常" },
  { id: 2, bikeId: "BIKE-042", date: "2026-05-11 18:15",
    duration: "25:00", wheel_wobble: "正常",
    chain_noise: "异常", handlebar: "正常" },
  { id: 3, bikeId: "BIKE-018", date: "2026-05-10 07:45",
    duration: "08:20", wheel_wobble: "正常",
    chain_noise: "正常", handlebar: "异常" },
];
```

每个卡片显示：单车编号、日期、时长、三个故障状态标签（绿色正常 / 红色异常）。

---

## 组件层

### FaultIndicator

**文件：** `components/FaultIndicator.tsx`
**Props：** `{ wheel?, chain?, handlebar? }` — 每个为 `FaultInfo` 类型

```typescript
interface FaultInfo {
  detected: "normal" | "suspect" | "fault" | "unknown";
  confidence: number;   // 0~1
  detail: string;
}
```

**显示逻辑：**

| detected | 颜色 | 中文标签 |
|----------|------|---------|
| normal | 🟢 `#22c55e` | 正常 |
| suspect | 🟡 `#f59e0b` | 疑似异常 |
| fault | 🔴 `#ef4444` | 故障 |
| unknown | ⚪ `#9ca3af` | 未检测 |

每行显示：图标 + 名称 + 状态标签 + 置信度百分比。

### SensorCollector

**文件：** `components/SensorCollector.tsx`
**Props：** `{ active: boolean, onDataFlush: (buffer: SensorBuffer) => void }`

包装 `sensorCollector` 服务的 UI 组件，显示实时样本计数和采集指示灯（灰/绿）。

```typescript
useEffect(() => {
  if (active) {
    sensorCollector.start(onFlush); // 启动传感器 + 注册每 100 样本回调
    return () => { sensorCollector.stop(); };
  }
}, [active]);
```

### RideStats

**文件：** `components/RideStats.tsx`
**Props：** `{ duration: number, distance: number, avgSpeed: number }`

三列行内展示：时长 (MM:SS) | 距离 (km) | 均速 (km/h)。竖线分隔，白色圆角卡片。

---

## 服务层

### API 客户端 (`services/api.ts`)

**Base URL 配置：**
```typescript
const BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";
```

**通用请求函数：**
```typescript
async function request<T>(endpoint: string, options?: ApiOptions): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }
  const res = await fetch(`${BASE_URL}${endpoint}`, { ... });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

**导出函数：**

| 函数 | HTTP | 路径 |
|------|------|------|
| `register(username, password)` | POST | `/api/auth/register` |
| `login(username, password)` | POST | `/api/auth/login` |
| `startRide(bikeId, lat, lng, token)` | POST | `/api/rides/start` |
| `endRide(rideId, lat, lng, token)` | POST | `/api/rides/{id}/end` |
| `uploadSensorData(rideId, accel, gyro, timestamps, token)` | POST | `/api/rides/{id}/sensor-data` |
| `detectWheelWobble(rideId, data, sampleRate, token)` | POST | `/api/detection/wheel-wobble/{id}` |
| `detectHandlebarMisalignment(rideId, data, sampleRate, token)` | POST | `/api/detection/handlebar/{id}` |
| `getDetectionReport(rideId, token)` | GET | `/api/detection/report/{id}` |

**注意：** `login` 使用 `x-www-form-urlencoded` 格式（FastAPI OAuth2PasswordRequestForm 要求），
其他请求均为 JSON。

### 传感器采集器 (`services/sensors.ts`)

**类：** `SensorCollector`（单例导出 `sensorCollector`）

```
配置:
  DEFAULT_INTERVAL_MS = 50    (20 Hz)
  BUFFER_FLUSH_SIZE = 100     (每 5 秒 flush)

内部:
  accelBuffer: SensorDataPoint[]
  gyroBuffer:  SensorDataPoint[]
  accelSub:     Subscription | null
  gyroSub:      Subscription | null
  onFlush:      callback
```

**方法：**
- `start(onFlush)` — 注册回调，开始监听两个传感器。buffers 达 100 个样本时自动 flush。
- `stop()` — 移除所有订阅，flush 剩余数据，返回 `SensorBuffer`。
- `flush()` (private) — 调用 `onFlush` 并清空缓冲区。

**辅助函数：**
- `checkSensorsAvailable()` → `Promise<{accelerometer: boolean, gyroscope: boolean}>` — 运行时检查传感器可用性

### 录音器 (`services/audioRecorder.ts`)

**类：** `AudioRecorder`（单例导出 `audioRecorder`）

**方法：**
- `start()` — 请求麦克风权限 → 设置音频模式 → 创建 HIGH_QUALITY 录音
- `stop()` — 停止录音并卸载 → 返回文件 URI（或 null）
- `getIsRecording()` — 返回当前录音状态

---

## Hooks

### useAuth

**文件：** `hooks/useAuth.ts`

```typescript
function useAuth() {
  // State: user, token, loading
  // Methods:
  //   login(username, password)  → 调用 api.login + /me
  //   register(username, password) → 调用 api.register + login
  //   logout() → 清除 user 和 token
  return { user, token, loading, login, register, logout };
}
```

---

## 工具函数 (`utils/formatters.ts`)

| 函数 | 输入 | 输出示例 |
|------|------|---------|
| `formatDuration(seconds)` | `125` | `"02:05"` |
| `formatDate(isoString)` | `"2026-05-12T08:30:00Z"` | `"2026年5月12日 08:30"` |
| `formatConfidence(value)` | `0.85` | `"85%"` |

---

## 应用配置 (`app.json`)

```json
{
  "expo": {
    "name": "bikeSharing",
    "slug": "bikesharing",
    "scheme": "bikesharing",
    "orientation": "portrait",
    "newArchEnabled": true,
    "ios": {
      "infoPlist": {
        "NSMicrophoneUsageDescription": "用于检测单车链条异响",
        "NSMotionUsageDescription": "用于检测单车轮胎偏摆和车头不正"
      }
    },
    "android": {
      "permissions": [
        "RECORD_AUDIO",
        "ACCESS_FINE_LOCATION",
        "ACTIVITY_RECOGNITION"
      ]
    },
    "plugins": ["expo-router", "expo-sensors", "expo-av"]
  }
}
```

---

## 开发注意事项

1. **传感器只能在真机上测试** — 模拟器不支持加速度计/陀螺仪/麦克风
2. **Expo Go 限制** — 某些原生模块在 Expo Go 中可能受限，
   使用 `npx expo run:android` / `npx expo run:ios` 编译开发版本
3. **环境变量** — 使用 `EXPO_PUBLIC_` 前缀使其在客户端 JS 中可用
4. **网络地址** — 真机测试时 `localhost` 指向手机本身，
   需将 `EXPO_PUBLIC_API_URL` 设置为电脑的局域网 IP
