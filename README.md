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
- Expo CLI (`npm install -g expo-cli`)

### 启动后端

```bash
docker-compose up -d              # 启动 PostgreSQL + Redis
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd app && uvicorn main:app --reload
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
