# 01 — 系统架构

## 概述

bikeSharing 是一个基于智能手机传感器（加速度计、陀螺仪、麦克风）的共享单车故障智能检测平台。
用户只需将手机固定在车把上骑行，系统即可自动检测三大常见故障：轮胎偏摆、链条异响、车头不正，
无需任何额外硬件。

**核心设计原则：**

- **零额外硬件** — 仅使用手机自带传感器
- **实时反馈** — 骑行结束即时给出检测结果
- **算法可迭代** — 支持从阈值法到 ML 模型的渐进升级
- **前后端分离** — RESTful API，移动端可独立开发

---

## 系统全景

```
┌─────────────────────────────────────────────────────────────┐
│                      移动端 (React Native + Expo)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ 页面层    │  │ 组件层    │  │ 服务层    │  │ Hooks       │ │
│  │ index.tsx │  │ Fault    │  │ api.ts    │  │ useAuth.ts  │ │
│  │ ride.tsx  │  │ Indicator │  │ sensors   │  │             │ │
│  │ history   │  │ RideStats │  │ .ts       │  │             │ │
│  │ .tsx      │  │ Sensor    │  │ audio     │  │             │ │
│  │           │  │ Collector │  │ Recorder  │  │             │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │
│                                                             │
│  传感器接口: Accelerometer / Gyroscope / Microphone          │
│  采样频率: 20Hz (加速度计+陀螺仪) / 44.1kHz (麦克风)         │
└─────────────────────┬───────────────────────────────────────┘
                      │  HTTPS / REST
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   后端 (Python FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ API 路由层    │  │ 服务层        │  │ 数据模型层          │ │
│  │ auth.py      │  │ sensor_      │  │ user.py            │ │
│  │ rides.py     │  │ analysis.py  │  │ ride.py            │ │
│  │ detection.py │  │ audio_       │  │ fault_report.py    │ │
│  │              │  │ analysis.py  │  │                    │ │
│  │              │  │ fault_       │  │                    │ │
│  │              │  │ classifier.py│  │                    │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│                                                             │
│  中间件: CORS / OAuth2PasswordBearer                         │
│  序列化: Pydantic v2 (schemas/__init__.py)                   │
└──────────┬──────────────────────┬───────────────────────────┘
           │                      │
           ▼                      ▼
    ┌─────────────┐      ┌──────────────┐
    │ PostgreSQL   │      │    Redis      │
    │ (主存储)      │      │  (缓存/队列)   │
    │              │      │              │
    │ users        │      │ 待实现:       │
    │ rides        │      │ - session    │
    │ fault_reports│      │ - task queue │
    └─────────────┘      │ - realtime   │
                         └──────────────┘
```

---

## 技术栈详情

### 移动端

| 技术 | 版本 | 用途 |
|------|------|------|
| React Native | 0.76.5 | 跨平台移动框架 |
| Expo | ~52.0.0 | RN 工具链 + 托管服务 |
| Expo Router | ~4.0.0 | 文件系统路由（类似 Next.js App Router） |
| expo-sensors | ~14.0.0 | 加速度计 + 陀螺仪访问 |
| expo-av | ~15.0.0 | 麦克风录音 |
| TypeScript | ~5.3.3 | 类型安全 |

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11 | 运行时 |
| FastAPI | 0.115+ | 异步 Web 框架 |
| Uvicorn | 0.34+ | ASGI 服务器 |
| Pydantic | 2.10+ | 数据验证/序列化 |
| SQLAlchemy | 2.0+ | ORM（异步引擎 + AsyncSession，Auth + Rides 均已持久化） |
| python-jose | 3.3+ | JWT 令牌签发与验证 |
| passlib + bcrypt | 1.7 / 3.2 | 密码哈希 |

### 信号处理 / ML

| 技术 | 版本 | 用途 |
|------|------|------|
| NumPy | 2.2+ | 数值计算基础 |
| SciPy | 1.14+ | FFT 频谱分析（未来使用） |
| librosa | 0.10+ | 音频特征提取（MFCC 等） |
| scikit-learn | 1.6+ | ML 分类器（SVM/RF，未来使用） |

### 基础设施

| 技术 | 版本 | 用途 |
|------|------|------|
| Docker Compose | 3.8+ | 本地开发环境编排 |
| PostgreSQL | 16-alpine | 关系数据库 |
| Redis | 7-alpine | 缓存 / 任务队列 |
| GitHub Actions | — | CI/CD（测试 + 构建检查） |

---

## 数据流

### 一次完整的骑行检测流程

```
1. 用户打开 App → AuthProvider 自动注册/登录 → 首页 (index.tsx)
2. 输入/扫描单车编号 → 点击"开始骑行"
   └── 调用 POST /api/rides/start → 创建骑行记录 (PostgreSQL) → 获取 rideId
3. 跳转骑行页面 (ride.tsx)，接收 { bikeId, rideId }
   ├── 启动 sensorCollector (20Hz, 缓冲 100 样本)
   │   ├── Accelerometer.addListener → accelBuffer
   │   └── Gyroscope.addListener → gyroBuffer
   ├── 每 100 样本自动 flush → POST /api/rides/{id}/sensor-data
   └── 累积全部数据供最终检测使用
4. 用户点击"结束骑行"
   ├── 停止传感器，上传最后一批数据
   ├── 调用 POST /api/rides/{id}/end → 更新骑行状态 (PostgreSQL)
   ├── 调用 POST /api/detection/wheel-wobble/{id}  → 轮胎检测
   ├── 调用 POST /api/detection/chain-noise/{id}    → 链条检测
   └── 调用 POST /api/detection/handlebar/{id}      → 车头检测
5. 显示检测结果 (FaultIndicator 组件): normal/suspect/fault + 置信度
6. 历史页面 (history.tsx) → GET /api/rides/ → 展示真实骑行记录
```

### 数据采集协议

```
传感器原始数据格式:
{
  x: float,        // X轴分量 (m/s² 或 rad/s)
  y: float,        // Y轴分量
  z: float,        // Z轴分量 (陀螺仪Z轴 = 偏航角)
  timestamp: float  // Unix 时间戳 (秒)
}

上传格式 (WheelWobbleRequest):
{
  "accelerometer_data": [
    {"x": 0.12, "y": 0.05, "z": 9.81, "timestamp": 0.0},
    ...
  ],
  "sample_rate": 50.0
}
```

---

## 关键设计决策

### 1. 20Hz 采样率（加速度计+陀螺仪）

**理由：** 轮胎旋转频率在骑行速度 10-20 km/h 时约为 2-4 Hz，
根据奈奎斯特采样定理，20Hz 足以捕获 10Hz 以下的信号。
同时考虑手机电池消耗，20Hz 是精度与功耗的平衡点。

### 2. 批量上传（每 100 样本）

**理由：** 每次 HTTP 请求有固定开销（TLS 握手、头部等）。
批量上传 100 个样本（约 5 秒数据）相比逐条发送可将网络请求减少 100 倍，
且延迟仍可接受（用户感受不到 5 秒的批处理滞后）。

### 3. 服务端检测（非端侧推理）

**理由：**
- 算法需要频繁迭代和调参，服务端部署可以无感更新
- Python 科学计算生态（numpy/scipy/librosa）比 JS/RN 更成熟
- 未来 ML 模型的加载和推理也更适合服务端
- 缺点：需要网络连接，对离线场景不友好（后续可考虑端侧备选方案）

### 4. 阈值法先行，ML 渐进替代

**理由：** 当前使用 RMS/统计阈值作为基线，代码简单、可解释。
后续可逐步替换为 FFT 频谱分析 → MFCC 特征 + SVM/RF → 深度学习。
服务层接口已抽象好（返回 `{detected, confidence, detail}`），
算法升级只需修改服务函数内部实现。

### 5. React Native + Expo（非原生开发）

**理由：**
- 跨平台（iOS + Android）一套代码
- Expo 托管了传感器权限、音频权限等原生模块，无需编写原生桥接
- Expo Router 提供了熟悉的文件系统路由
- 快速原型开发，适合学生/小团队项目

---

## 目录结构

```
bikeSharing/
├── mobile/                  # React Native (Expo) 移动应用
│   ├── app/                 # 页面 (Expo Router 文件路由)
│   │   ├── _layout.tsx      # 根布局 (Stack)
│   │   └── (tabs)/          # Tab 导航
│   │       ├── _layout.tsx  # Tab 配置
│   │       ├── index.tsx    # 首页（开始骑行）
│   │       ├── ride.tsx     # 骑行中（传感器+检测）
│   │       └── history.tsx  # 历史记录
│   ├── components/          # 可复用组件
│   ├── services/            # 业务服务层（API/传感器/录音）
│   ├── hooks/               # 自定义 Hooks
│   └── utils/               # 工具函数
├── backend/                 # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口 + 路由挂载
│   │   ├── config.py        # 配置管理 (pydantic-settings)
│   │   ├── api/             # API 路由模块
│   │   │   ├── auth.py      # 认证 (注册/登录/JWT)
│   │   │   ├── rides.py     # 骑行管理
│   │   │   └── detection.py # 故障检测
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 序列化模型
│   │   ├── services/        # 业务逻辑（检测算法）
│   │   └── utils/           # 工具函数
│   └── tests/               # 测试
├── ml/                      # ML 实验
│   ├── notebooks/           # Jupyter 笔记本
│   ├── data/                # 数据目录（原始+处理后）
│   └── models/              # 训练好的模型文件
├── docs/                    # 项目文档 (本目录)
├── .github/workflows/       # CI/CD 配置
├── docker-compose.yml       # 本地开发环境
├── environment.yml          # Conda 环境定义
└── README.md
```

---

## 组件交互矩阵

| 调用方 | 被调用方 | 协议 | 说明 |
|--------|---------|------|------|
| Mobile `api.ts` | Backend `/api/auth/*` | HTTPS POST/GET | 注册、登录、获取用户信息 |
| Mobile `api.ts` | Backend `/api/rides/*` | HTTPS POST/GET | 骑行生命周期管理 |
| Mobile `api.ts` | Backend `/api/detection/*` | HTTPS POST/GET | 故障检测请求 |
| Mobile `sensors.ts` | expo-sensors `Accelerometer` | Native API | 加速度计读数 (20Hz) |
| Mobile `sensors.ts` | expo-sensors `Gyroscope` | Native API | 陀螺仪读数 (20Hz) |
| Mobile `audioRecorder.ts` | expo-av `Audio.Recording` | Native API | 麦克风录音 (44.1kHz) |
| Backend `detection.py` | `sensor_analysis.py` | Python import | 轮胎偏摆分析 |
| Backend `detection.py` | `audio_analysis.py` | Python import | 链条异响分析 |
| Backend `detection.py` | `fault_classifier.py` | Python import | 车头不正分析 |
| Backend `auth.py` | `python-jose` + `passlib` | Python import | JWT 签发 + bcrypt 哈希 |

---

## 安全设计

| 层面 | 措施 | 状态 |
|------|------|------|
| 传输 | HTTPS（生产环境） | 待部署 |
| 认证 | JWT HS256, 60分钟过期 | 已实现 |
| 密码存储 | bcrypt 哈希 (passlib) | 已实现 |
| CORS | 当前 `allow_origins=["*"]` | 开发阶段，上线需收紧 |
| 密钥管理 | `SECRET_KEY` 从环境变量/`.env` 读取 | 已实现 |
| 输入验证 | Pydantic 模型自动校验所有请求体 | 已实现 |

---

## 下一步架构演进

1. **DB 集成** ✅ — Auth + Rides 已通过 SQLAlchemy AsyncSession 接入 PostgreSQL（32 测试通过）
2. **Redis 集成** — 实现会话缓存、检测任务队列
3. **FFT/MFCC 实现** — 升级阈值法为频谱分析
4. **故障检测持久化** — 检测结果写入 fault_reports 表
5. **实时推送** — WebSocket 推送检测进度
6. **端侧备选** — 对关键场景提供离线检测能力
