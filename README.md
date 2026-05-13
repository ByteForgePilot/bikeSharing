# bikeSharing — 共享单车故障智能检测平台

基于手机传感器（加速度计、陀螺仪、麦克风）检测共享单车三大常见故障，无需额外硬件。

## 检测能力

| 故障类型 | 传感器 | 检测方法 | 表现特征 |
|---------|--------|---------|---------|
| 🛞 轮胎偏摆 | 加速度计 | FFT 频谱分析 | 1-5Hz 周期性振动 |
| 🔗 链条异响 | 麦克风 | MFCC + 异常检测 | "咔咔"声 / 高频摩擦 |
| 🔧 车头不正 | 陀螺仪 | 偏航角分析 | 系统性方向偏移 |

## 技术栈

| 层 | 选型 |
|---|------|
| 移动端 | React Native (Expo) |
| 后端 | Python FastAPI |
| 数据库 | PostgreSQL + Redis |
| 信号处理 | scipy + numpy |
| ML | scikit-learn |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Conda / Miniforge（推荐）或 venv
- Expo CLI (`npm install -g expo-cli`)

### 启动后端

**方式一：Conda（推荐）**

```bash
# 创建环境（首次）
conda env create -f environment.yml

# 激活环境
conda activate bikeSharing

# 后续更新环境
conda env update -f environment.yml --prune

# 启动服务
docker compose up -d db redis     # 启动 PostgreSQL + Redis
cd backend
set PYTHONPATH=.
uvicorn app.main:app --reload
```

**方式二：venv + pip**

```bash
docker compose up -d db redis     # 启动 PostgreSQL + Redis
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=.
uvicorn app.main:app --reload
```

### 启动移动端

```bash
cd mobile
npm install expo-linking --legacy-peer-deps  # expo-router 必需依赖
npm install
npx expo start
```

> 无后端时自动进入离线模式，数据存本地文件。APK 构建见 [运行指南 §9](docs/11-run-guide.md#9-构建独立-apk)。

### 运行测试

```bash
cd backend && pytest -v
# 32 个测试全部通过：3 API + 23 服务层 + 6 数据库集成
```

## 项目结构

```
bikeSharing/
├── mobile/          # React Native (Expo) 移动端
├── backend/         # Python FastAPI 后端
├── ml/              # ML 模型训练 & 实验
├── docs/            # 项目文档
└── .github/         # CI/CD 配置
```

## 文档索引

| 文档 | 说明 | 适合 |
|------|------|------|
| [01-架构](docs/01-architecture.md) | 系统全景、技术选型、数据流 | 全体 |
| [02-API](docs/02-api-reference.md) | 14 个端点完整参考 | 后端/移动端 |
| [03-数据库](docs/03-database-design.md) | ER 图、DDL、ORM 模型 | 后端 |
| [04-算法](docs/04-fault-detection-algorithms.md) | 三种检测算法数学原理 | 算法/后端 |
| [05-传感器](docs/05-sensor-guide.md) | 手机固定、采样配置、数据格式 | 移动端/算法 |
| [06-移动端](docs/06-mobile-development.md) | Expo 架构、页面/组件/服务 | 移动端 |
| [07-ML](docs/07-ml-pipeline.md) | 实验环境、特征工程、模型训练 | 算法 |
| [08-部署](docs/08-devops-deployment.md) | Docker、CI/CD、环境变量 | 后端/全体 |
| [09-测试](docs/09-testing-strategy.md) | 32 个测试的分层结构（3层：API + 服务 + DB集成） | 全体 |
| [10-协作](docs/10-development-workflow.md) | Git 工作流、环境管理、FAQ | 全体 |
| [11-运行指南](docs/11-run-guide.md) | 从零到运行的完整步骤+排查 | 全体 |
| [00-团队配置指南](docs/00-team-setup.md) | 新队友零基础配置（极详细） | 新成员 |

## 小组分工

| 角色 | 人数 | 职责 |
|------|------|------|
| 后端工程师 | 1-2 | FastAPI、数据库、API |
| 移动端工程师 | 1-2 | React Native、传感器、UI |
| 算法工程师 | 1-2 | 信号处理、音频分析、ML |

## 参与开发

### 1. 克隆仓库

```bash
git clone https://github.com/ByteForgePilot/bikeSharing.git
cd bikeSharing
```

### 2. 搭建环境

- 后端/算法：`conda env create -f environment.yml && conda activate bikeSharing`
- 移动端：`cd mobile && npm install`

### 3. 开发流程

```bash
git checkout -b feature/你的功能名    # 从 main 新建分支
# ... 写代码 ...
git add .
git commit -m "做了什么改动"
git push -u origin feature/你的功能名
# 到 GitHub 页面创建 Pull Request
```

### 4. 运行测试（提交前必做）

```bash
docker compose up -d db redis     # 启动依赖服务
cd backend && pytest -v           # 32 个测试应全部通过
```
