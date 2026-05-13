# 06 — 移动端开发指南

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React Native | 0.76.5 | 跨平台移动框架 |
| Expo | 52.0.0 | RN 工具链 + 托管环境 |
| Expo Router | 4.0.0 | 文件系统路由 |
| expo-sensors | 14.0.0 | 加速度计 + 陀螺仪 |
| expo-av | 15.0.0 | 麦克风录音 |
| expo-file-system | ~18.0.0 | 本地文件存储 |
| expo-linking | ~7.0.0 | 深链接 (expo-router 依赖) |
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
// 外层包裹 AuthProvider（自动注册/登录，提供全局认证状态）
<AuthProvider>
  <Stack>
    <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
  </Stack>
</AuthProvider>
```

AuthProvider 在应用启动时自动生成设备 ID 并注册/登录，后续所有页面通过 `useAuthContext()` 获取 token。

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

**功能：** 全中文界面，输入单车编号创建骑行记录。支持在线/离线双模式。

**State:**
- `bikeId: string` — 单车编号输入值
- `starting: boolean` — 正在创建骑行记录

**交互流程：**
```
1. App 启动 → AuthProvider 自动注册/登录 + 检测后端可达性
2. 顶部显示在线🟢/离线📱状态徽章
3. 输入 bike_id（支持回车提交）或点击📷扫码按钮
4. 点击"🚴 开始骑行检测"（按钮带按压动画）
5. 在线: POST /api/rides/start → 后端创建 PostgreSQL 记录
   离线: 本地生成 rideId，调用 offlineStorage.createRide()
6. router.push({ pathname: '/(tabs)/ride', params: { bikeId, rideId } })
```

**UI 亮点：**
- Hero 区大图标 + 应用名「共享单车故障检测」+ 副标题
- 在线/离线状态徽章实时显示
- 三个检测项用彩色卡片网格 (蓝/黄/绿)
- 底部使用提示卡片
- 按钮带缩放假动画

---

### 骑行页 (`ride.tsx`)

**功能：** 真实传感器采集（20Hz 缓冲），可视化进度条展示数据，在线/离线双模式，结束骑行时执行检测

**接收参数：** `{ bikeId: string, rideId: string }`

**交互亮点：**
- **深色计时器头部** — 车辆编号 + 48px 大字计时器 + 状态指示
- **旋转活动指示环** — 数据采集中自动旋转动画
- **动态彩色进度条** — 替代原始 XYZ 数字，超阈值自动变黄/红
- **结束按钮带阴影和图标** — 红色醒目按钮，检测中显示 loading
- **离线保存提示** — 离线模式下结束骑行显示 "✅ 数据已保存到本地"

**传感器进度条颜色逻辑：**
| 数值范围 | 颜色 | 含义 |
|----------|------|------|
| < 40% 量程 | 🟢 绿色 | 正常 |
| 40%-70% 量程 | 🟡 黄色 | 注意 |
| > 70% 量程 | 🔴 红色 | 异常 |

**State:**
- `elapsed: number` — 已骑行秒数 (timer 每秒 +1)
- `accelLatest / gyroLatest: SensorDataPoint | null` — 最新传感器读数
- `sampleCount: number` — 累计采集样本数
- `uploading: boolean` — 正在上传
- `ending: boolean` — 正在结束
- `wheelResult / chainResult / handlebarResult: FaultResult | null` — 检测结果

**离线模式流程：**
```typescript
// 离线时传感器数据写入本地文件
await offlineStorage.saveSensorChunk(rideId, accelBuffer, gyroBuffer);
// 结束骑行时保存最终数据
await offlineStorage.finishRide(rideId, accelAll, gyroAll, SAMPLE_RATE);
// 结果显示 "数据已保存到本地"
```

---

### 历史页 (`history.tsx`)

**功能：** 在线从后端拉取骑行历史，离线读取本地文件。支持筛选和展开详情。

**交互亮点：**
- **统计概览** — 顶部三列数字：全部 / 进行中 / 已完成
- **筛选标签** —「全部」「已完成」「进行中」三 Tab 切换
- **点击展开卡片** — 展开显示骑行时长、起止时间、数据来源，LayoutAnimation 动画
- **进行中标识** — 左侧黄色边框高亮
- **智能空状态** — 根据当前筛选显示不同文案
- **下拉刷新** — FlatList onRefresh

**State:**
- `rides: RideItem[]` — 骑行记录列表
- `filter: "全部" | "已完成" | "进行中"` — 当前筛选
- `expandedIds: Set<string>` — 已展开的卡片 ID
- `loading / error` — 加载和错误状态

**在线/离线双数据源：**
```typescript
if (online && token) {
  data = await api.getRides(token, 50, 0);      // GET /api/rides/
} else {
  metas = await offlineStorage.listRides();       // 读取本地文件
}
```

---

## 组件层

### FaultIndicator

**文件：** `components/FaultIndicator.tsx` ⏺ 已集成于 `ride.tsx`
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
可替代直接调用 `sensorCollector` 单例，适合需要独立 UI 展示采集状态的场景。

> 注意：`ride.tsx` 当前直接使用 `services/sensors.ts` 的 `sensorCollector` 单例而非此组件。
> 此组件保留为可选的封装方式。

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
| `startRide(bikeId, lat, lng, token)` | POST | `/api/rides/start` → `{ ride: { id, ... }, message }` |
| `endRide(rideId, lat, lng, token)` | POST | `/api/rides/{id}/end` |
| `getRides(token, limit?, offset?)` | GET | `/api/rides/` → `{ rides, total, limit, offset }` |
| `getRide(rideId, token)` | GET | `/api/rides/{id}` |
| `uploadSensorData(rideId, accel, gyro, sampleRate, token)` | POST | `/api/rides/{id}/sensor-data` |
| `detectWheelWobble(rideId, data, sampleRate, token)` | POST | `/api/detection/wheel-wobble/{id}` → `{ wheel_wobble: {...} }` |
| `detectChainNoise(rideId, features, token)` | POST | `/api/detection/chain-noise/{id}` → `{ chain_noise: {...} }` |
| `detectHandlebarMisalignment(rideId, data, sampleRate, token)` | POST | `/api/detection/handlebar/{id}` → `{ handlebar_misalignment: {...} }` |
| `getDetectionReport(rideId, token)` | GET | `/api/detection/report/{id}` |

所有函数均有明确的 TypeScript 返回类型，`uploadSensorData` 发送 `sample_rate`（非 `timestamps` 数组）。

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

### 离线存储 (`services/offlineStorage.ts`)

**用途：** 无后端网络时的本地文件持久化，使用 `expo-file-system` 在 `documentDirectory` 下存储 JSON 文件。

**文件结构：**
```
documentDirectory/rides/
├── meta.json           # 骑行记录索引
├── {rideId}_meta.json  # 单条记录元数据
├── {rideId}_data.json  # 传感器数据
└── {rideId}_chunk_*.json # 分块传感器数据
```

**导出函数：**

| 函数 | 说明 |
|------|------|
| `isBackendReachable()` | 3 秒超时 health check 检测后端可达性 |
| `createRide(rideId, bikeId)` | 创建本地骑行记录 |
| `finishRide(rideId, accelData, gyroData, sampleRate)` | 结束并保存完整数据 |
| `saveSensorChunk(rideId, accelBuffer, gyroBuffer)` | 追加传感器分块 |
| `listRides()` | 列出所有本地骑行记录 |
| `getRide(rideId)` | 读取单条记录详情 |

**数据格式 (`OfflineRideMeta`)：**
```typescript
interface OfflineRideMeta {
  rideId: string;
  bikeId: string;
  startedAt: string;
  endedAt: string | null;
  status: string;
}
```

---

## Hooks

### AuthContext (主要认证方案)

**文件：** `hooks/AuthContext.tsx`

`AuthProvider` 包裹根布局，提供全局认证状态。启动时自动用设备 ID 注册/登录。

```typescript
// 所有子页面通过 useAuthContext() 获取:
const { user, token, loading, online, login, register, logout } = useAuthContext();
```

- `loading` — 首次认证/后端检测进行中时为 true（首页据此显示 loading）
- `online` — 后端可达时为 true，离线时为 false
- `token` — Bearer token（离线时为 null），所有 API 调用需要
- 启动时先 `isBackendReachable()` 检测，不可达则进入离线模式
- 可达时自动生成用户名 `rider_<random>`，密码 `bike1234` 注册/登录

### useAuth (独立 Hook，备选)

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

> 当前页面前面使用 `AuthContext`，此 hook 保留为不依赖 Context 的备选方案。

---

## 工具函数 (`utils/formatters.ts`)

| 函数 | 输入 | 输出示例 | 使用者 |
|------|------|---------|--------|
| `formatDuration(seconds)` | `125` | `"02:05"` | — |
| `formatDate(isoString)` | `"2026-05-12T08:30:00Z"` | `"2026年5月12日 08:30"` | history.tsx |
| `formatConfidence(value)` | `0.85` | `"85%"` | FaultIndicator |

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
2. **环境变量** — 使用 `EXPO_PUBLIC_` 前缀使其在客户端 JS 中可用
3. **网络地址** — 真机测试时 `localhost` 指向手机本身，需将 `EXPO_PUBLIC_API_URL` 设置为电脑的局域网 IP

---

## APK 构建

### 前提条件

| 工具 | 版本 | 说明 |
|------|------|------|
| Android Studio | 2025.3+ | 含 Android SDK、Gradle |
| JDK 17 | 17.0.x (Temurin) | React Native Gradle Plugin 要求 |
| Android SDK Platform | 34 | `File → Settings → Android SDK` 安装 |
| Android SDK Build-Tools | 最新 | SDK Tools 标签页安装 |

### 构建步骤

1. **Android Studio → File → Open** → 选择 `mobile/android` 目录
2. 等待 Gradle Sync 完成（首次 10-20 分钟）
3. **Build Variants** → 将 `app` 从 `debug` 切换为 `release`
4. **Build → Build APK(s)**
5. 等待 `:app:createBundleReleaseJsAndAssets` 完成
6. 右下角弹出提示 → **locate** → APK 位于 `android/app/build/outputs/apk/release/app-release.apk`

> **为什么用 release 模式？** debug 版 APK 不打包 JS 代码，运行时需连接 Metro 开发服务器。release 版将 JS bundle 内嵌到 APK 中，可独立运行。

### 依赖安装注意事项

`expo-linking` 是 `expo-router` 的必需依赖但不会自动安装：

```bash
cd mobile
npm install expo-linking --legacy-peer-deps
```

### Gradle 配置

项目已配置以下国内镜像加速：

- **Gradle 分发包**: `mirrors.cloud.tencent.com` (gradle-wrapper.properties)
- **Maven 仓库**: `maven.aliyun.com` (build.gradle)
- **Kotlin 版本**: `1.9.25` (与 Compose Compiler 1.5.15 兼容)
