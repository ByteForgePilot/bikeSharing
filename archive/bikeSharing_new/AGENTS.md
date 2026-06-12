# 仓库指南

## 项目结构

```
bikrsharing/
├── BicycleDataLogger/          # 原生 Android 数据采集 App (Kotlin, Jetpack Compose)
│   └── app/src/main/java/com/bicycle/datalogger/
│       ├── sensors/            # AccelCollector, GyroCollector, GpsCollector, AudioCollector, SensorService
│       └── ui/screens/         # Compose UI
├── data/                       # 真实传感器数据 + 独立检测运行器
│   ├── 传感器数据.txt            # 加速度计 + 陀螺仪 + GPS CSV
│   ├── 音频.pcm                  # 16-bit LE PCM 音频
│   ├── 音频_时间戳.csv            # 音频时间戳映射
│   ├── run_detection.py         # 独立检测脚本（无需服务器）
│   ├── 2/                         # 第二组测试数据
│   │   └── 传感器数据(2).txt / 音频(2).pcm / 音频_时间戳(2).csv
│   └── 3/                         # 第三组测试数据（轮毂和车头不正）
│       └── 传感器数据(6).txt / 音频(6).pcm / 音频_时间戳(6).csv
├── backend/
│   └── app/
│       ├── api/                # FastAPI 路由处理（auth, rides, detection）
│       ├── core/               # JWT 安全
│       ├── ml/                 # 检测算法 v3.0 (bike_health_detector.py)
│       ├── models/             # SQLAlchemy ORM (User, Ride, FaultReport)
│       ├── repositories/       # 数据库访问层
│       ├── schemas/            # Pydantic 请求/响应模型
│       ├── services/           # 业务逻辑 + 检测引擎适配器
│       └── templates/          # ECharts 仪表板 HTML (Jinja2)
│   └── tests/                  # pytest (test_detection_engine, test_api, test_rides_db)
├── docs/                       # 项目文档 (00-09)
├── docker-compose.yml          # PostgreSQL + Redis + 后端
└── AGENTS.md                   # 本文件
```

## 构建、测试与开发命令

```bash
# 全栈 (Docker)
docker compose up -d                            # db + redis + 后端，端口 :8000

# 本地后端开发（独立模式，无需 Docker/DB）
cd backend
python -m uvicorn app.main:app --reload --port 8000   # 仪表板 + /process 接口
                                                       # DB 接口会优雅报错

# 安装依赖
cd backend && pip install -r requirements.txt

# 在真实数据上运行检测（无需服务器）
cd bikrsharing
python data/run_detection.py                          # 读取 data/ 文件，打印并保存 JSON

# 运行测试
cd backend && pytest tests/ -v                          # 全部测试
cd backend && pytest tests/test_detection_engine.py -v   # 仅检测引擎
cd backend && pytest tests/test_api.py -v                # API 集成测试

# Android 构建
cd BicycleDataLogger && ./gradlew assembleDebug
```

## 编码风格与命名

- **Python**：4 空格缩进。遵循 PEP 8。函数签名使用类型注解。
- **Python 编码**：所有 .py 文件必须使用 UTF-8 **无 BOM**。避免 UTF-16LE（会导致 "null bytes" SyntaxError）。
- **Kotlin**：标准 Kotlin 约定。4 空格缩进。
- **文件命名**：Python 模块使用 snake_case，Kotlin 类使用 PascalCase。
- **数据库列**：snake_case，与 SQLAlchemy ORM 属性一致。
- 当前阶段不强制使用格式化工具或 linter。

## 测试指南

- 框架：pytest + pytest-asyncio（用于异步测试）。
- 测试文件：`tests/test_<模块>.py`。
- 测试类：`Test<功能>` 分组相关用例。
- 覆盖重点：检测引擎（F1/F2/F3 管线）、API 接口、数据库操作。
- 最少数据：合成传感器数据（_make_accel、_make_gyro、_make_audio 辅助函数）。

## 提交与 PR 指南

- 提交信息：中文或英文。格式：`<版本/标签>: <摘要>`（例如 `v3.0: Integrate algorithm v3.0`）。
- 保持提交聚焦 —— 每次提交一个逻辑变更。
- PR 应包括：变更简述、新增依赖说明、测试结果。
- 关联相关 issue。

## 架构说明

- **检测管线**：BicycleDataLogger -> CSV/PCM 文件 -> POST /api/detection/upload/{ride_id} -> detection_engine.py -> bike_health_detector.py (v3.2) -> PostgreSQL 中的 FaultReport。
- **独立模式**：后端启动时无需 PostgreSQL/Redis。/api/detection/dashboard 和 /api/detection/process 可独立工作。process 接口直接使用 app.services.detection_engine，不经过 DB 层。
- **data/run_detection.py**：在本地传感器数据上运行全量检测（F1/F2/F3 + 综合评分），无需任何服务器基础设施。结果保存到 data/detection_result.json。
- **仪表板**：通过 Jinja2 Environment + ECharts 在 /api/detection/dashboard 提供服务。模板目录为 app/templates（相对于 backend/）。
- **评分**：三个子分数（0-100）通过加权调和平均 + 最小值惩罚因子（"木桶效应"）合成。
- **F3 v3.2 车头不正检测**：3.1 版修复了自适应窗口选择切断信号的问题，改为传全量陀螺仪数据。用直行段 gz 中位偏置 × 实际观察时长（上限 30s）替代固定 T_obs=2s。健康阈值从 8° 降到 3°。3.2 版新增加速度计辅助检测：三轴去重力残差幅度的稳定性比值（直行段 std/全程 std）检测骑行者因车头不正产生的侧向补偿晃动。当陀螺仪偏置小（Δθ₁ < 3°）但稳定性比值大（> 0.55）时施加惩罚放大等效角度。此方法与手机安装方向无关（去重力后算三轴总残差幅度）。
- **认证**：基于 JWT。首次启动时使用设备 ID 自动注册。

## 已知问题

- **文件编码**：源 .py 文件必须为 UTF-8 无 BOM。部分文件最初保存为 UTF-16LE（导致 "null bytes" SyntaxError）。出现编码问题时，使用 `git show HEAD:<file>` 恢复原始文件。
- **网络依赖构建**：Docker 构建需要网络进行 pip install；企业防火墙可能阻止 PyPI。可使用 `python -m uvicorn`（本地）和 `python data/run_detection.py` 作为替代方案。
- **仪表板模板路径**：从 backend/ 目录运行 uvicorn 时，模板目录必须为 app/templates（相对路径，不是 backend/app/templates）。
- **ECharts 图表渲染**：仪表板的 ECharts 图表默认被隐藏（display: none），初始化时容器尺寸为 0 导致图表不能正常渲染。在显示结果区块后新增了 chart.resize() 调用（通过 setTimeout 100ms 等待布局重算）。此修复覆盖了“开始检测”按钮和服务端预加载两个路径。


## 安全与配置

- 将 .env.example 复制为 .env 进行本地覆盖（默认值适用于 Docker）。
- 部署到生产环境前必须更改 SECRET_KEY。
- API 接口需要 Bearer 令牌，以下接口除外：/api/health、/api/auth/*、/api/detection/dashboard、/api/detection/process。
- 切勿提交 .env 或凭据。
