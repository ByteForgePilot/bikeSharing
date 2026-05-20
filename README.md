# bikeSharing — 共享单车故障智能检测平台

基于手机传感器（加速度计、陀螺仪、麦克风）检测共享单车三大常见故障，无需额外硬件。

## 检测能力

| 故障类型 | 传感器 | 检测方法 | 表现特征 |
|---------|--------|---------|---------|
| 🛞 轮胎偏摆 | 加速度计 | RMS 振动能量分析 | 横向/垂向异常振动 |
| 🔗 链条异响 | 麦克风 (MFCC) | 特征向量异常检测 | "咔咔"声 / 高频摩擦 |
| 🔧 车头不正 | 陀螺仪 | 偏航角均值偏移 | 直线骑行系统性偏向 |

## 一键启动 (Docker)

```bash
git clone git@github.com:ByteForgePilot/bikeSharing.git
cd bikeSharing
docker compose up -d               # 后端全家桶: DB + Redis + Backend
# 或 算法同学:
docker compose --profile ml up -d  # 后端 + Jupyter Lab
```

启动后：

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| Jupyter Lab | http://localhost:8888 (需 `--profile ml`) |

```bash
curl http://localhost:8000/api/health  # → {"status":"ok"}
```

> **仅需 Docker Desktop**，不需要装 Python/Conda/Node。首次启动自动拉取镜像 + pip install，约 3-5 分钟。

## 项目结构

```
bikeSharing/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                # auth, rides, detection 路由 (12 端点)
│   │   ├── models/             # SQLAlchemy ORM (User, Ride, FaultReport)
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 检测算法 (传感器/音频/故障分类)
│   │   ├── config.py           # 配置管理 (pydantic-settings)
│   │   ├── database.py         # 异步数据库引擎 + 会话
│   │   └── main.py             # 应用入口
│   ├── tests/                  # 32 个测试 (API + 服务 + DB 集成)
│   ├── requirements.txt        # Python 依赖清单
│   └── Dockerfile              # python:3.12-slim
├── mobile/                     # React Native Expo 移动端
│   ├── app/                    # expo-router 页面 (3 Tab: 骑行/检测/历史)
│   ├── components/             # FaultIndicator, RideStats, SensorCollector
│   ├── hooks/                  # AuthContext (自动注册登录)
│   ├── services/               # API 调用, 传感器采集, 音频录制, 离线存储
│   ├── android/                # Expo prebuild 生成的 Android 原生项目
│   └── build_apk.ps1           # APK 构建脚本
├── ml/                         # ML 实验
│   ├── notebooks/              # Jupyter 探索性分析
│   ├── data/                   # 传感器数据 (待采集)
│   └── models/                 # 训练好的模型 (待训练)
├── docs/                       # 14 份项目文档
├── docker-compose.yml          # PostgreSQL 16 + Redis 7 + Backend
├── environment.yml             # Conda 环境 (Python 3.11 全家桶)
├── .github/workflows/          # CI/CD (后端测试 + 移动端类型检查)
└── .env.example                # 环境变量模板
```

## 技术栈

### 后端

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行环境 |
| FastAPI | >=0.115 | Web 框架 |
| Uvicorn | >=0.34 | ASGI 服务器 |
| SQLAlchemy | >=2.0 | ORM (async 模式) |
| asyncpg | >=0.30 | PostgreSQL 异步驱动 |
| Alembic | >=1.14 | 数据库迁移 |
| Pydantic | >=2.10 | 数据验证 |
| python-jose | >=3.3 | JWT 编码/解码 |
| passlib + bcrypt | >=1.7 | 密码哈希 |
| numpy | >=2.2 | 数值计算 |
| scipy | >=1.14 | 科学计算 (FFT) |
| librosa | >=0.10 | 音频分析 (MFCC) |
| scikit-learn | >=1.6 | 机器学习 |
| redis | >=5.2 | Redis 客户端 |
| httpx | >=0.28 | HTTP 测试客户端 |

### 移动端

| 依赖 | 版本 | 用途 |
|------|------|------|
| react-native | 0.76.5 | 跨平台框架 |
| expo | ~52.0.0 | Expo SDK |
| expo-router | ~4.0.0 | 文件系统路由 |
| expo-sensors | ~14.0.0 | 加速度计/陀螺仪 |
| expo-av | ~15.0.0 | 音频录制 |
| expo-location | ~18.0.0 | GPS 定位 |
| expo-file-system | ~18.0.12 | 离线存储 |
| typescript | ~5.3.3 | 类型检查 |

### 基础设施

| 组件 | 镜像/版本 | 端口 |
|------|----------|------|
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| Backend | 本地构建 (python:3.12-slim) | 8000 |

## 启动方式

### 方式一：Docker 全家桶（推荐，团队统一环境）

```bash
docker compose up -d                 # 后端开发者
docker compose --profile ml up -d    # 算法开发者 (含 Jupyter)
```

所有依赖在容器内统一管理，团队成员环境完全一致，消除 "我电脑上能跑" 问题。

### 方式二：Docker 基础设施 + 本地开发

适合 IDE 调试、频繁改代码的场景。

```bash
# 启动数据库和缓存
docker compose up -d db redis

# 后端（选一种）
conda env create -f environment.yml && conda activate bikeSharing   # Conda
# 或
cd backend && pip install -r requirements.txt                       # venv

# 启动开发服务器
cd backend && uvicorn app.main:app --reload
```

### 移动端

```bash
cd mobile
npm install
npx expo start                    # 开发服务器 (二维码/USB)
# 或构建 APK
.\build_apk.ps1                   # 需要 JDK 17 + Android SDK
```

> 无后端时自动进入离线模式，数据存本地文件。

### 运行测试

```bash
docker compose up -d              # 确保 db + redis 运行中
cd backend && pytest -v           # 32 个测试全部通过
```

## 环境变量

```bash
cp .env.example .env              # 复制模板
# 编辑 .env，修改 SECRET_KEY（生产必须更换）
```

关键变量说明：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...@localhost/bikesharing` | Docker 内用 `db` 主机名 |
| `REDIS_URL` | `redis://localhost:6379` | Docker 内用 `redis` 主机名 |
| `SECRET_KEY` | `change-me-in-production` | JWT 签名密钥，生产必换 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | JWT 过期时间 |
| `SENSOR_SAMPLE_RATE` | 50 | 加速度计/陀螺仪采样率 (Hz) |
| `EXPO_PUBLIC_API_URL` | `http://localhost:8000` | 移动端 API 地址 |

Docker Compose 启动时会自动将 `localhost` 替换为容器主机名 (`db`/`redis`)，无需手动修改 `.env`。

## API 端点 (12 个)

### 认证 `/api/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 用户注册 |
| POST | `/login` | OAuth2 登录，返回 JWT |
| GET | `/me` | 当前用户信息 |

### 骑行 `/api/rides`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/start` | 开始骑行 |
| POST | `/{id}/end` | 结束骑行 |
| POST | `/{id}/sensor-data` | 上传传感器数据 |
| POST | `/{id}/audio` | 上传音频片段 |
| GET | `/` | 骑行历史 (分页) |
| GET | `/{id}` | 骑行详情 |

### 检测 `/api/detection`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/wheel-wobble/{ride_id}` | 轮胎偏摆检测 |
| POST | `/chain-noise/{ride_id}` | 链条异响检测 |
| POST | `/handlebar/{ride_id}` | 车头不正检测 |
| GET | `/report/{ride_id}` | 综合检测报告 |

> 完整 API 参数、示例、错误码详见 [API 参考文档](docs/02-api-reference.md)

## 文档导航

| 文档 | 内容 | 适合 |
|------|------|------|
| [00-团队配置指南](docs/00-team-setup.md) | 零基础工具安装 (60-90min) | 新成员 |
| [01-架构](docs/01-architecture.md) | 系统全景、技术选型、数据流 | 全体 |
| [02-API 参考](docs/02-api-reference.md) | 14 端点完整参考 | 后端/移动端 |
| [03-数据库设计](docs/03-database-design.md) | ER 图、DDL、ORM 模型 | 后端 |
| [04-故障检测算法](docs/04-fault-detection-algorithms.md) | 三种检测算法数学原理 | 算法/后端 |
| [05-传感器指南](docs/05-sensor-guide.md) | 手机固定、采样配置、数据格式 | 移动端/算法 |
| [06-移动端开发](docs/06-mobile-development.md) | Expo 架构、页面/组件/服务 | 移动端 |
| [07-ML 流水线](docs/07-ml-pipeline.md) | 实验环境、特征工程、模型训练 | 算法 |
| [08-部署运维](docs/08-devops-deployment.md) | Docker、CI/CD、环境变量 | 后端/全体 |
| [09-测试策略](docs/09-testing-strategy.md) | 32 测试的分层结构 | 全体 |
| [10-协作流程](docs/10-development-workflow.md) | Git 工作流、环境管理、FAQ | 全体 |
| [11-运行指南](docs/11-run-guide.md) | 从零到运行的完整步骤+排查 | 全体 |

## 检测数据流

```
[移动端 App]
    │ 加速度计 20Hz + 陀螺仪 20Hz
    ├─ POST /api/auth/register ──→ users 表
    ├─ POST /api/auth/login    ──→ JWT Token
    ├─ POST /api/rides/start   ──→ rides 表 (status=active)
    ├─ POST /api/rides/{id}/sensor-data ──→ 传感器数据上传
    ├─ POST /api/rides/{id}/end         ──→ rides 表 (status=completed)
    ├─ POST /api/detection/wheel-wobble/{id} ──→ RMS 振动分析 ──→ normal/suspect/fault
    ├─ POST /api/detection/chain-noise/{id}  ──→ 特征异常检测 ──→ normal/suspect/fault
    └─ POST /api/detection/handlebar/{id}    ──→ 偏航均值分析 ──→ normal/suspect/fault
```

## 数据库模型

| 表 | 关键字段 | 说明 |
|----|---------|------|
| `users` | id, username, password_hash, created_at | 用户账户 |
| `rides` | id, user_id→users, bike_id, lat/lng, status, started_at | 骑行记录 |
| `fault_reports` | id, ride_id→rides, 三种检测结果+置信度+详情 | 故障报告 |

## 参与开发

```bash
git checkout -b feature/功能名          # 从 main 新建分支
# ... 写代码 ...
git add . && git commit -m "描述改动"
git push -u origin feature/功能名
# 到 GitHub 创建 Pull Request
```

**提交前必做：**
```bash
cd backend && pytest -v                # 32 个测试必须全部通过
```

## 许可证

MIT
