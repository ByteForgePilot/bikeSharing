# CLAUDE.md — bikeSharing 项目总览

## 项目简介

共享单车故障智能检测平台。通过手机传感器（加速度计、陀螺仪、麦克风）采集骑行数据，检测三大常见故障：轮胎偏摆、链条异响、车头不正。

## 技术栈

| 层 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | >=0.115 |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async | 16-alpine |
| 缓存 | Redis 7 | 7-alpine |
| 认证 | JWT (HS256) + bcrypt | — |
| 移动端 | React Native + Expo SDK 52 | RN 0.76.5 |
| 路由 | expo-router 4.0 (Tab 导航) | — |
| 信号处理 | scipy + numpy + librosa | >=1.14 |
| ML | scikit-learn + joblib | >=1.6 |
| 基础设施 | Docker Compose + GitHub Actions | — |
| Python | 3.11 (conda) / 3.12 (Docker) | — |
| Node | 20+ | — |

## 目录结构

```
bikeSharing/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/                # 路由: auth.py, rides.py, detection.py
│   │   ├── models/             # ORM: user.py, ride.py, fault_report.py
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 检测算法: sensor_analysis, audio_analysis, fault_classifier
│   │   ├── config.py           # pydantic-settings 配置 (从 .env 读)
│   │   ├── database.py         # SQLAlchemy async engine + session
│   │   └── main.py             # 应用入口 (lifespan, CORS, 路由)
│   ├── tests/                  # 32 个测试 (API + 服务 + DB集成)
│   │   ├── conftest.py         # 独立测试DB + async fixtures
│   │   ├── test_api.py         # 3 用例: health, register/login, detection
│   │   ├── test_rides_db.py    # 7 用例: 骑行全流程+隔离+分页
│   │   └── test_services.py    # 22 用例: 三种检测算法全覆盖
│   ├── Dockerfile              # python:3.12-slim + libsndfile1
│   ├── requirements.txt        # Python 依赖
│   └── pytest.ini              # asyncio_mode = auto
├── mobile/                     # React Native Expo 移动端
│   ├── app/                    # expo-router 页面
│   │   ├── _layout.tsx         # 根布局 (AuthProvider + Stack)
│   │   └── (tabs)/             # Tab 导航
│   │       ├── index.tsx       # Tab1 骑行入口 (输入bike_id)
│   │       ├── ride.tsx        # Tab2 实时检测 (传感器可视化)
│   │       └── history.tsx     # Tab3 历史记录 (筛选+展开)
│   ├── components/             # FaultIndicator, RideStats, SensorCollector
│   ├── hooks/                  # AuthContext.tsx (自动注册登录)
│   ├── services/               # api.ts, sensors.ts, audioRecorder.ts, offlineStorage.ts
│   ├── utils/                  # formatters.ts
│   ├── android/                # Expo prebuild 生成的原生 Android 项目
│   └── build_apk.ps1           # APK 构建脚本
├── ml/                         # ML 实验
│   ├── notebooks/              # Jupyter notebooks (探索性分析)
│   ├── data/raw/ + processed/  # 传感器数据 (待采集)
│   └── models/                 # 训练好的模型 (待训练)
├── docs/                       # 14 份项目文档 (00-11 系列)
├── docker-compose.yml          # 3 服务: db + redis + backend
├── environment.yml             # Conda 环境定义
├── .env.example                # 环境变量模板
├── .github/workflows/          # CI: backend-test.yml, mobile-build.yml
└── README.md
```

## Docker-first 快速启动（推荐）

```bash
docker compose up -d                # 后端全家桶: PostgreSQL + Redis + Backend
# 或
docker compose --profile ml up -d   # 后端 + Jupyter Lab ML 环境

# 后端健康检查
curl http://localhost:8000/api/health  # → {"status":"ok","version":"0.1.0"}
# API 文档: http://localhost:8000/docs
# Jupyter:   http://localhost:8888 (如果启用了 ml profile)
```

仅需 Docker Desktop，首次启动自动拉取镜像 + pip install，约 3-5 分钟。不需要安装 Python/Conda/Node。

## 常用命令

### 后端开发

```bash
# 仅启动基础设施，后端本地跑（热重载开发）
docker compose up -d db redis
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 运行所有测试 (需要 db + redis 已启动)
cd backend && pytest -v               # 32 passed

# 进入容器调试
docker compose exec backend bash
docker compose exec db psql -U postgres -d bikesharing
docker compose exec redis redis-cli

# 查看日志
docker compose logs -f backend
```

### 移动端开发

```bash
cd mobile
npm install
npx expo start                    # 启动 Expo Dev Server

# 构建 Debug APK (需要 Android SDK + JDK 17)
.\build_apk.ps1
```

### ML 实验

```bash
docker compose --profile ml up -d  # 启动 Jupyter Lab
# 浏览器打开 http://localhost:8888
# 数据挂载: ./ml → /home/jovyan/work
# 后端代码: ./backend → /home/jovyan/backend (只读参考)
```

### 运维

```bash
docker compose down                # 停止所有服务
docker compose down -v             # 停止 + 清空数据库（重置开发环境）
docker compose restart backend     # 重启后端（代码改动后自动热重载已生效）
```

## 环境变量

所有配置通过 `.env` 文件或环境变量注入，后端使用 pydantic-settings 自动读取。详见 `.env.example`。

关键变量:
- `DATABASE_URL` — Docker 内用 `db` 主机名，本地用 `localhost`
- `SECRET_KEY` — 生产必须更换，用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成

## 文档导航

| 角色 | 推荐阅读顺序 |
|------|-------------|
| 新成员 | `docs/00-team-setup.md` → `docs/01-architecture.md` → `docs/11-run-guide.md` |
| 后端 | `docs/01-architecture.md` → `docs/02-api-reference.md` → `docs/03-database-design.md` → `docs/09-testing-strategy.md` |
| 移动端 | `docs/01-architecture.md` → `docs/05-sensor-guide.md` → `docs/06-mobile-development.md` |
| 算法 | `docs/01-architecture.md` → `docs/04-fault-detection-algorithms.md` → `docs/07-ml-pipeline.md` |
| DevOps | `docs/01-architecture.md` → `docs/08-devops-deployment.md` |

## API 端点一览 (12 个)

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `POST` | `/api/auth/register` | 用户注册 | 无 |
| `POST` | `/api/auth/login` | 登录 (OAuth2 form) | 无 |
| `GET` | `/api/auth/me` | 当前用户信息 | Bearer |
| `POST` | `/api/rides/start` | 开始骑行 | Bearer |
| `POST` | `/api/rides/{id}/end` | 结束骑行 | Bearer |
| `POST` | `/api/rides/{id}/sensor-data` | 上传传感器数据 | Bearer |
| `POST` | `/api/rides/{id}/audio` | 上传音频片段 | Bearer |
| `GET` | `/api/rides/` | 骑行历史 (分页) | Bearer |
| `GET` | `/api/rides/{id}` | 骑行详情 | Bearer |
| `POST` | `/api/detection/wheel-wobble/{id}` | 轮胎偏摆检测 | Bearer |
| `POST` | `/api/detection/chain-noise/{id}` | 链条异响检测 | Bearer |
| `POST` | `/api/detection/handlebar/{id}` | 车头不正检测 | Bearer |
| `GET` | `/api/detection/report/{id}` | 综合检测报告 | Bearer |

## Git 工作流

```bash
git checkout -b feature/功能名   # 从 main 新建分支
# ... 开发 ...
git add . && git commit -m "描述改动"
git push -u origin feature/功能名
# GitHub 创建 Pull Request
```

提交前务必运行 `cd backend && pytest -v`，32 个测试必须全部通过。
