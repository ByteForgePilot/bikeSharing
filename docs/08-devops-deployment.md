# 08 — 部署与运维

## 概述

项目使用 Docker Compose 编排本地开发环境，GitHub Actions 做 CI/CD。
数据库使用 PostgreSQL 16 + Redis 7。

---

## 本地开发环境

### 前置条件

- Docker Desktop（唯一必需）
- Node.js 20+（仅移动端开发需要）
- Python/Conda 不再必需 — Docker 已管理所有 Python 依赖

### 一键启动（团队统一环境）

```bash
docker compose up -d                 # 后端全家桶: DB + Redis + Backend (含热重载)
docker compose --profile ml up -d    # 加 Jupyter Lab (算法开发)

# 验证
curl http://localhost:8000/api/health  # → {"status":"ok"}
```

### 本地开发模式

```bash
docker compose up -d db redis        # 仅基础设施
cd backend && uvicorn app.main:app --reload  # 后端本地跑 (IDE 调试)
```

---

## Docker Compose 拓扑

```yaml
services:
  db:        # PostgreSQL 16 Alpine (5432)
  redis:     # Redis 7 Alpine (6379, 持久化)
  backend:   # FastAPI (从 Dockerfile 构建, 8000, 热重载)
  jupyter:   # Jupyter Lab (profile: ml, 8888, 可选)
```

### 服务间网络

```
host.docker.internal / localhost
┌──────────────────────────────┐
│  宿主机                       │
│  ┌─────────┐  ┌───────────┐  │
│  │ Backend │  │  Mobile   │  │
│  │ :8000   │  │ Expo      │  │
│  └────┬────┘  └───────────┘  │
└───────┼──────────────────────┘
        │ localhost:5432, localhost:6379
        ▼
┌──────────────────────────────┐
│  Docker 网络                  │
│  ┌──────────┐ ┌───────────┐  │
│  │   db     │ │  redis    │  │
│  │  :5432   │ │  :6379    │  │
│  └──────────┘ └───────────┘  │
└──────────────────────────────┘
```

### 各服务配置详情

**PostgreSQL (`db`)**
```yaml
image: postgres:16-alpine
environment:
  POSTGRES_USER: ${POSTGRES_USER:-postgres}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
  POSTGRES_DB: ${POSTGRES_DB:-bikesharing}
ports: "5432:5432"
volumes:
  - pgdata:/var/lib/postgresql/data   # 数据持久化
healthcheck:
  test: pg_isready -U postgres
  interval: 5s, timeout: 3s, retries: 5
```

**Redis (`redis`)**
```yaml
image: redis:7-alpine
ports: "6379:6379"
volumes:
  - redisdata:/data                   # RDB/AOF 持久化
healthcheck:
  test: redis-cli ping
  interval: 5s, timeout: 3s, retries: 5
```

**Backend (`backend`)**
```yaml
build: ./backend                       # python:3.12-slim
ports: "8000:8000"
environment:                           # 使用 ${VAR:-default} fallback
  DATABASE_URL: ...@db:5432/...
  REDIS_URL: redis://redis:6379
  SECRET_KEY: ${SECRET_KEY:-...}
depends_on:
  db: { condition: service_healthy }
  redis: { condition: service_healthy }
volumes:
  - ./backend:/app                     # 热重载
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Jupyter (`jupyter`, 可选)**
```yaml
image: jupyter/scipy-notebook:python-3.11
profiles: [ml]                         # docker compose --profile ml up
ports: "8888:8888"
volumes:
  - ./ml:/home/jovyan/work             # Notebook 工作目录
  - ./backend:/home/jovyan/backend     # 后端代码参考
```

注意：Docker 内的 backend 连接 `db` 和 `redis` 使用 Compose 服务名（Docker DNS 解析），
宿主机直接运行时连接 `localhost`。

---

## Backend Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# librosa 依赖的音频库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**镜像分层策略：**
- Layer 1: 系统依赖 (`libsndfile1`)
- Layer 2: pip install (依赖变更少时缓存有效)
- Layer 3: 应用代码 (变更最频繁)

---

## 环境变量

所有配置通过 `Settings` (pydantic-settings) 管理，优先级: 环境变量 > `.env` 文件 > 默认值。

### 环境变量

所有配置通过 `backend/app/config.py` (pydantic-settings) 管理，优先级: 环境变量 > `.env` 文件 > 默认值。

**初始化：** `cp .env.example .env`，然后按需修改。
完整变量清单见 `.env.example`。

### 生成 SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# 输出示例: a1b2c3d4e5f6...（64字符十六进制）
```

**重要：** 生产环境必须修改 `SECRET_KEY`！默认值 `change-me-in-production` 仅用于本地开发。

---

## 常用运维命令

### 查看日志

```bash
docker compose logs -f backend    # 后端日志
docker compose logs -f db         # 数据库日志
docker compose logs -f --tail=100 # 最近 100 行
```

### 进入容器调试

```bash
docker compose exec db psql -U postgres -d bikesharing  # PostgreSQL CLI
docker compose exec redis redis-cli                      # Redis CLI
docker compose exec backend bash                         # 后端容器 Shell
```

### 数据库操作

```bash
# 重置数据库（删除所有数据）
docker compose down -v   # -v 删除 volumes
docker compose up -d     # 重新创建

# 备份数据库
docker compose exec db pg_dump -U postgres bikesharing > backup.sql

# 恢复数据库
docker compose exec -T db psql -U postgres bikesharing < backup.sql
```

### 清理

```bash
docker compose down            # 停止服务，保留 volumes
docker compose down -v         # 停止服务 + 删除 volumes
docker system prune -a         # 清理所有未使用的镜像/容器/网络
```

---

## CI/CD (GitHub Actions)

### Backend Tests (`backend-test.yml`)

**触发条件：** push 或 PR 到 `backend/**` 路径

```yaml
name: Backend Tests
on:
  push:
    paths: ['backend/**']
  pull_request:
    paths: ['backend/**']

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: bikesharing }
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready --health-interval 5s --health-timeout 3s --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
        options: >-
          --health-cmd "redis-cli ping" --health-interval 5s --health-timeout 3s --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && pytest -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/bikesharing
          DATABASE_URL_SYNC: postgresql://postgres:postgres@localhost:5432/bikesharing
          REDIS_URL: redis://localhost:6379
```

### Mobile Build Check (`mobile-build.yml`)

**触发条件：** push 或 PR 到 `mobile/**` 路径

```yaml
name: Mobile Build Check
on:
  push:
    paths: ['mobile/**']
  pull_request:
    paths: ['mobile/**']

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: mobile/package-lock.json }
      - run: npm ci
        working-directory: mobile
      - run: npx tsc --noEmit
        working-directory: mobile
```

---

## 生产部署（规划）

### 推荐架构

```
┌────────────┐     ┌──────────────┐     ┌──────────────┐
│  Nginx     │────►│  FastAPI      │────►│  PostgreSQL  │
│  (HTTPS)   │     │  (gunicorn)   │     │  (RDS)       │
│  :443      │     │  :8000 × N    │     └──────────────┘
└────────────┘     └──────────────┘     ┌──────────────┐
                                        │  Redis       │
                                        │  (ElastiCache)│
                                        └──────────────┘
```

**待讨论：**
- 云平台选择（AWS / 阿里云 / 腾讯云）
- 是否使用托管数据库（RDS）vs 自建
- CI/CD 中是否加入 Docker 镜像构建和推送
- Expo 移动端发布方式（OTA Update vs App Store 审核）
