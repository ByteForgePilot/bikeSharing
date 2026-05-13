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
docker-compose up -d              # 启动 PostgreSQL + Redis
cd backend
uvicorn app.main:app --reload
```

**方式二：venv + pip**

```bash
docker-compose up -d              # 启动 PostgreSQL + Redis
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 启动移动端

```bash
cd mobile
npm install
npx expo start
```

### 运行测试

```bash
cd backend && pytest
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
docker-compose up -d              # 启动依赖服务
cd backend && pytest              # 26 个测试应全部通过
```
