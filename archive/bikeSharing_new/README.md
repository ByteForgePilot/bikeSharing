# bikeSharing -- 共享单车故障检测平台

基于智能手机传感器的共享单车故障检测：骑行、采集传感器数据、实时获取健康评分。

## 系统架构

```
BicycleDataLogger (Android 数据采集 App)
    加速度计 100Hz + 陀螺仪 50Hz + GPS 10Hz + 音频 8kHz PCM
        |
        |  POST /api/detection/upload/{ride_id} (传感器 CSV + PCM + 时间戳)
        v
FastAPI 后端 (端口 8000)
    |
    +-- /api/auth/*           JWT 认证
    +-- /api/rides/*          骑行生命周期（开始/结束/数据）
    +-- /api/detection/upload 三级全量检测
    +-- /api/detection/*      各故障独立接口
    +-- /api/detection/dashboard   ECharts 网页仪表板
    |
    v
检测引擎 (v3.0)
    F1: 轮胎偏摆   -- FFT + 车轮频率分析
    F2: 链条异响   -- 包络谱 + 倒谱分析
    F3: 车头不正   -- 陀螺仪偏航偏差 + 直行段检测
    综合: 加权调和平均 + 惩罚因子 (0-100)
    |
    v
PostgreSQL + Redis
```

## 快速开始

### 1. Docker（推荐）

```bash
cp .env.example .env      # 可选，默认值即可运行
docker compose up -d       # 启动 db + redis + 后端，端口 8000
```

后端首次启动时自动创建数据库表。仪表板访问 http://localhost:8000/api/detection/dashboard。

### 2. 本地开发

```bash
# 仅启动基础设施
docker compose up -d db redis

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 启动
uvicorn app.main:app --reload --port 8000
```

### 3. 独立运行模式（无需 Docker）

```bash
# 后端启动，无需 PostgreSQL/Redis
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 无需数据库时可用的接口：
#   GET  /api/detection/dashboard   -- ECharts 仪表板
#   POST /api/detection/process     -- 文件上传检测（无需认证）

# 需要数据库的接口（auth、rides、upload）会优雅地返回错误。
```

### 4. 在本地传感器数据上运行检测

```bash
# 无需服务器 -- 直接在 data/ 目录上运行检测
cd bikrsharing
python data/run_detection.py

# 读取 data/传感器数据.txt + 音频.pcm + 音频_时间戳.csv
# 运行 F1/F2/F3 + 综合健康评分
# 将详细结果保存到 data/detection_result.json
```

data/ 目录包含 BicycleDataLogger 采集的真实传感器数据，可直接用于测试检测管线。

### 5. 移动端数据采集

在 Android Studio 中打开 `BicycleDataLogger/`，构建并安装 APK。App 采集以下数据：
- 加速度计 @ 100Hz
- 陀螺仪 @ 50Hz
- GPS @ 10Hz（支持网络定位备选）
- 音频 @ 8kHz 16-bit PCM 单声道

骑行数据保存到 `Documents/自行车数据/<timestamp>/`，包含三个文件：
- `传感器数据.txt` -- CSV：timestamp_ns, sensor_type, ax, ay, az, lat, lng, speed, course, gx, gy, gz
- `音频.pcm` -- 16-bit 小端 PCM
- `音频_时间戳.csv` -- timestamp_ns, cumulative_samples

将这三个文件上传到 `POST /api/detection/upload/{ride_id}` 进行全量分析。

## API 概览

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册设备账号 |
| POST | `/api/auth/login` | 获取 JWT 令牌 |
| POST | `/api/rides/start` | 开始骑行 |
| POST | `/api/rides/{id}/end` | 结束骑行 |
| POST | `/api/rides/{id}/sensor-data` | 上传传感器读数 |
| POST | `/api/rides/{id}/audio` | 上传音频用于链条检测 |
| POST | `/api/detection/upload/{id}` | 上传 BicycleDataLogger 文件进行全量检测 |
| POST | `/api/detection/process` | 独立文件上传检测（无需认证） |
| GET | `/api/detection/report/{id}` | 获取检测报告 |
| GET | `/api/detection/health-score/{id}` | 获取综合健康评分 |
| GET | `/api/detection/dashboard` | 网页可视化仪表板 |

完整 Swagger 文档访问 http://localhost:8000/docs。

## 检测系统 (v3.0)

使用手机内置传感器进行三项故障检测：

1. **F1 轮胎偏摆** -- 对 Z 轴加速度做 FFT 分析。提取车轮旋转频率并计算偏摆特征 P = A1 + 0.5*A2。使用平坦路面窗口选择确保读数可靠。

2. **F2 链条异响** -- 对 8kHz 音频做包络谱分析。希尔伯特变换提取踏板频率包络，结合 SNR + 谐波检测 + 倒谱周期分析，区分链条冲击与环境噪声。

3. **F3 车头不正** -- 陀螺仪 Z 轴偏航偏差检测。选择直行路段（最低 gz 方差的窗口），计算等效转向偏角。

**综合评分**：加权调和平均（0.4/0.3/0.3）配合最小值惩罚因子（"木桶效应"——单个严重故障拉低总分）。

| 评分 | 等级 | 建议 |
|------|------|------|
| >= 70 | 良好 | 推荐骑行 |
| 50-69 | 注意 | 谨慎使用 |
| < 50 | 较差 | 建议换车 |

## 项目结构

```
bikrsharing/
+-- data/                  真实传感器数据 + 检测运行器
|   +-- run_detection.py   独立检测脚本（无需服务器）
|   +-- 传感器数据.txt       加速度计/陀螺仪/GPS CSV
|   +-- 音频.pcm            16-bit LE PCM 音频
|   +-- 音频_时间戳.csv      音频时间戳映射
+-- BicycleDataLogger/     原生 Android 数据采集 App (Kotlin)
+-- backend/
|   +-- app/
|   |   +-- api/           FastAPI 路由处理
|   |   +-- core/          JWT 安全
|   |   +-- ml/            检测算法 v3.0
|   |   +-- models/        SQLAlchemy ORM 模型
|   |   +-- repositories/  数据库访问层
|   |   +-- schemas/       Pydantic 请求/响应模式
|   |   +-- services/      业务逻辑 + 检测引擎
|   |   +-- templates/     ECharts 仪表板 HTML
|   +-- tests/
+-- docs/                  项目文档
+-- docker-compose.yml     Docker 编排
```

## 测试

```bash
cd backend
pytest tests/test_detection_engine.py -v    # 检测算法测试
pytest tests/test_api.py -v                  # API 集成测试
pytest tests/test_rides_db.py -v             # 数据库测试
```
