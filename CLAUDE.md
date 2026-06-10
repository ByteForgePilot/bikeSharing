# CLAUDE.md -- bikeSharing 项目速查

## 项目简介

基于手机传感器的共享单车故障检测平台。
原生 Android 数据采集器 + FastAPI 后端 + v3.0 检测算法。

## 系统架构

```
BicycleDataLogger (Kotlin/Android) → 传感器数据.txt + 音频.pcm + 音频_时间戳.csv
                                                      ↓
FastAPI 后端 → detection_engine.py → bike_health_detector.py (v3.0)
                                                      ↓
                                           F1(轮胎) + F2(链条) + F3(车头) → 健康评分
                                                      ↓
                                           PostgreSQL (骑行记录 + 故障报告)
```

## 关键文件

| 文件 | 用途 |
|------|------|
| `backend/app/ml/bike_health_detector.py` | 核心检测算法 (v3.0)：F1 FFT 轮胎、F2 包络谱链条、F3 陀螺仪车头、综合评分 |
| `backend/app/services/detection_engine.py` | 适配器：将 API 数据格式转换为算法数据结构，文件解析，统一检测入口 |
| `backend/app/services/detection.py` | 编排：调用引擎，将结果存入数据库 |
| `backend/app/api/detection.py` | API 接口 + ECharts 仪表板 |
| `backend/app/models/fault_report.py` | 数据库模型：total_score、tire/chain/handlebar 分数、建议、details_json |
| `BicycleDataLogger/` | 原生 Android 应用 (Kotlin)：前台服务、100Hz 加速度计、50Hz 陀螺仪、10Hz GPS、8kHz PCM 音频 |

## 数据格式

**BicycleDataLogger 输出：**
- `传感器数据.txt`：CSV，含表头，列：timestamp_ns、type(加速度计/陀螺仪/GPS)、ax、ay、az、lat、lng、speed、course、gx、gy、gz
- `音频.pcm`：16-bit 小端 PCM，单声道，8kHz
- `音频_时间戳.csv`：timestamp_ns、cumulative_samples

**API JSON 格式**（单接口检测）：
```json
{
  "accelerometer_data": [{"x": 0.1, "y": 0.05, "z": 9.81, "timestamp": 0.0}, ...],
  "sample_rate": 100.0
}
```

## 常用命令

```bash
# 启动全栈
docker compose up -d

# 仅启动基础设施（开发模式）
docker compose up -d db redis

# 后端开发服务器
cd backend && uvicorn app.main:app --reload --port 8000

# 运行测试
cd backend && pytest tests/ -v

# 指定测试
cd backend && pytest tests/test_detection_engine.py -v
```

## 检测算法 (v3.0)

**F1 - 轮胎偏摆**：Z 轴加速度 → FFT → 车轮频率 f（通过 GPS 速度/半径计算）→ P = A1 + 0.5*A2 → 通过 P_healthy=0.15、P_severe=0.60 计算得分

**F2 - 链条异响**：8kHz 音频 → 2-4kHz 带通 → 希尔伯特包络 → 低通 0.5-10Hz → 包络频谱 SNR（踏板频率处）+ 谐波 + 相位一致性 + 倒谱 → 异常评分

**F3 - 车头不正**：陀螺仪 Z 轴 → 直行段选择（最低 30% gz 方差）→ gz 偏置 * 2s 观测 → delta_theta → 通过 5°/15° 阈值计算得分

**综合**：H = 1/(0.4/F1 + 0.3/F2 + 0.3/F3)、penalty = min(F1,F2,F3)/100、S = H * penalty

## 数据库

- `users`：id、username、password_hash
- `rides`：id、user_id、bike_id、start_lat/lng、end_lat/lng、status
- `fault_reports`：id、ride_id、total_score、tire_score、chain_score、handlebar_score、recommendation、details_json（+ 遗留的 detected/confidence 字段）

## 依赖

- 后端：FastAPI、SQLAlchemy async、PostgreSQL、Redis、numpy、scipy、Jinja2
- 移动端：Kotlin、Jetpack Compose、Android SensorManager、AudioRecord、LocationManager
