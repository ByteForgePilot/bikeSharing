# 11 — 运行指南

本文档提供从零开始运行 bikeSharing 项目的完整步骤。
预计总耗时：**30-45 分钟**（取决于网络和下载速度）。

---

## 1. 环境检查清单

开始前请确认以下工具已安装：

### 必需工具

| 工具 | 最低版本 | 验证命令 | 说明 |
|------|---------|---------|------|
| Git | 2.30+ | `git --version` | 克隆仓库和版本控制 |
| Docker Desktop | 20.10+ | `docker --version` | 运行 PostgreSQL + Redis |
| Conda / Miniforge | 23.0+ | `conda --version` | Python 环境管理（推荐） |
| Python | 3.11+ | `python --version` | 备选方案（不用 Conda 时） |
| Node.js | 20+ | `node --version` | 移动端开发 |
| npm | 9+ | `npm --version` | Node 包管理 |

### 可选工具

| 工具 | 用途 |
|------|------|
| VS Code | 推荐 IDE |
| GitHub CLI (`gh`) | GitHub 操作（PR、Issue 等） |
| Expo Go (手机 App) | 真机运行移动端（iOS App Store / Android 各应用商店下载） |

### 如果缺少工具

```bash
# Conda/Miniforge（推荐）
winget install CondaForge.Miniforge3
# 安装后重启终端

# Docker Desktop
winget install Docker.DockerDesktop

# Node.js
winget install OpenJS.NodeJS.LTS

# GitHub CLI
winget install GitHub.cli
```

---

## 2. 克隆仓库

```bash
git clone https://github.com/ByteForgePilot/bikeSharing.git
cd bikeSharing
```

预计耗时：< 30 秒

---

## 3. 启动基础设施（PostgreSQL + Redis）

### 3.1 确认 Docker 在运行

```bash
docker info
```

如果报错 "docker daemon is not running"：
- Windows/macOS：打开 Docker Desktop 应用，等待鲸鱼图标变绿
- Linux：`sudo systemctl start docker`

### 3.2 启动服务

```bash
docker-compose up -d
```

**预期输出：**
```
[+] Running 3/3
 ✔ Network bikesharing_default  Created
 ✔ Container bikesharing-db-1   Started
 ✔ Container bikesharing-redis-1 Started
```

### 3.3 验证服务状态

```bash
docker-compose ps
```

**预期输出（State 列应为 "healthy"）：**
```
NAME                   STATUS
bikesharing-db-1      Up (healthy)
bikesharing-redis-1   Up (healthy)
```

### 3.4 验证 PostgreSQL

```bash
docker-compose exec db psql -U postgres -c "SELECT 1 AS connected;"
```

**预期输出：**
```
 connected
-----------
         1
```

### 3.5 验证 Redis

```bash
docker-compose exec redis redis-cli PING
```

**预期输出：**
```
PONG
```

预计耗时：2-5 分钟（首次拉取镜像可能较慢）

---

## 4. 后端环境搭建

### 方式一：Conda（推荐）

#### 4.1 验证 Conda

```bash
conda --version
```

如果提示 `conda: command not found`：
- Windows：从开始菜单打开 "Miniforge Prompt" 或在 PowerShell 中运行 `C:\Users\<用户名>\miniforge3\Scripts\activate`
- macOS/Linux：运行 `conda init` 后重启终端

#### 4.2 创建环境

```bash
conda env create -f environment.yml
```

**预期输出（最后一行）：**
```
# To activate this environment, use
#     $ conda activate bikeSharing
```

预计耗时：5-15 分钟（首次需下载约 200+ 个包）

#### 4.3 激活环境

```bash
conda activate bikeSharing
```

终端提示符前应出现 `(bikeSharing)`。

#### 4.4 验证 Python 环境

```bash
python --version
# 预期：Python 3.11.15
```

```bash
python -c "import fastapi; import numpy; import scipy; import librosa; print('All imports OK')"
# 预期：All imports OK
```

#### 4.5 启动后端

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**预期输出：**
```
INFO:     Will watch for changes in these directories: ['E:\\Project\\bikeSharing\\backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 方式二：venv + pip（备选）

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

预计耗时：3-8 分钟

---

## 5. 后端验证

打开新的终端窗口，用 curl 测试各端点。

> PowerShell 用户：以下 curl 命令在 PowerShell 中需替换为 `curl.exe` 或使用 Postman 等 GUI 工具。

### 5.1 健康检查

```bash
curl http://localhost:8000/api/health
```

**预期输出：**
```json
{"status":"ok","version":"0.1.0"}
```

### 5.2 用户注册

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'
```

**预期输出：**
```json
{"id":1,"username":"testuser"}
```

### 5.3 用户登录

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass"
```

**预期输出（access_token 值会不同）：**
```json
{"access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer"}
```

### 5.4 获取当前用户（使用上一步的 token）

```bash
# 把 <TOKEN> 替换为上一步返回的 access_token
TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**预期输出：**
```json
{"id":1,"username":"testuser"}
```

### 5.5 轮胎偏摆检测

```bash
TOKEN="你的token"
curl -X POST http://localhost:8000/api/detection/wheel-wobble/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accelerometer_data": [
      {"x":0.12,"y":0.05,"z":9.81,"timestamp":0.0},
      {"x":0.15,"y":0.04,"z":9.79,"timestamp":0.02}
    ],
    "sample_rate": 50.0
  }'
```

**预期输出：**
```json
{"ride_id":1,"wheel_wobble":{"detected":"unknown","confidence":0.0,"detail":"Insufficient data (need >= 2 seconds)"}}
```

> 返回 `unknown` 和 `Insufficient data` 是正常的——测试只发了 2 个样本（0.04 秒），不足 2 秒。

### 5.6 查看 API 交互式文档

浏览器打开：http://localhost:8000/docs

FastAPI 自动生成的 Swagger UI，可直接在页面上测试所有 API。
（推荐用于快速探索和调试）

---

## 6. 运行测试

### 6.1 确认在 conda 环境 + backend 目录

```bash
conda activate bikeSharing
cd backend
```

### 6.2 运行全部测试

```bash
pytest -v
```

**预期输出：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.15, pytest-9.0.3

backend/tests/test_api.py::test_health_check PASSED                      [  3%]
backend/tests/test_api.py::test_register_and_login PASSED                [  7%]
backend/tests/test_api.py::test_wheel_wobble_detection PASSED            [ 11%]
backend/tests/test_services.py::TestWheelWobble::test_insufficient_data PASSED [ 15%]
...
backend/tests/test_services.py::TestHandlebar::test_return_keys PASSED   [100%]

============================= 26 passed in 1.19s ==============================
```

### 6.3 分模块运行

```bash
# 仅 API 集成测试
pytest tests/test_api.py -v

# 仅服务层单元测试
pytest tests/test_services.py -v

# 只测轮胎偏摆相关
pytest tests/test_services.py::TestWheelWobble -v

# 只测某个具体 case
pytest tests/test_services.py::TestHandlebar::test_outlier_trimming -v
```

---

## 7. 移动端环境搭建

### 7.1 确认 Node.js 版本

```bash
node --version  # 应 ≥ v20.0.0
npm --version   # 应 ≥ 9.0.0
```

### 7.2 安装依赖

```bash
cd mobile
npm install
```

预计耗时：2-5 分钟

### 7.3 配置 API 地址

如果真机测试，后端运行在电脑上，需要设置局域网 IP：

```bash
# Windows: 先查看本机 IP
ipconfig | findstr "IPv4"

# macOS/Linux:
ifconfig | grep "inet "

# 假设电脑 IP 是 192.168.1.100，创建环境变量
# 方式一：每次启动前设置
set EXPO_PUBLIC_API_URL=http://192.168.1.100:8000

# 方式二：写入 .env 文件（推荐）
echo "EXPO_PUBLIC_API_URL=http://192.168.1.100:8000" > .env
```

> 如果是在电脑模拟器上运行，默认 `http://localhost:8000` 即可。

### 7.4 启动 Expo

```bash
npx expo start
```

**预期输出：**
```
Starting project at E:\Project\bikeSharing\mobile

› Metro waiting on http://localhost:8081
› Web is waiting on http://localhost:8081

› Scan the QR code above with Expo Go (Android) or the Camera app (iOS)

› Press ? │ show all commands

› Press w • open web
› Press a • open Android
› Press i • open iOS
```

---

## 8. 移动端验证

### 8.1 在手机上运行

1. 在手机上安装 **Expo Go** App
2. 确保手机和电脑在**同一局域网**
3. 用 Expo Go 扫描终端中的**二维码**
4. 等待 JS Bundle 加载完成

### 8.2 验证首页功能

1. App 打开后显示首页（标题 "bikeSharing"）
2. 查看检测项目列表（轮胎偏摆、链条异响、车头不正）
3. 输入任意单车编号（如 `BIKE-001`）
4. 点击"开始骑行"

### 8.3 验证骑行页面

1. 页面跳转到骑行页，顶部显示单车编号和计时器
2. 传感器状态指示灯应为绿色（表示采集中）
3. 加速度计和陀螺仪数值应实时变化
4. 检测状态应在几秒后更新（模拟数据）

> 注意：传感器在模拟器上不工作，必须在真机上运行。

### 8.4 验证历史页面

1. 切换到"历史" Tab
2. 看到 3 条模拟历史记录
3. 每条记录显示单车编号、日期、时长和故障状态

### 8.5 检查传感器可用性

如果传感器数据不更新，可以添加调试代码验证：

```typescript
// 在 mobile/app/(tabs)/ride.tsx 的 useEffect 中临时添加
import { Accelerometer, Gyroscope } from 'expo-sensors';

Accelerometer.isAvailableAsync().then(a => console.log('Accel available:', a));
Gyroscope.isAvailableAsync().then(g => console.log('Gyro available:', g));
```

---

## 9. ML 环境搭建（算法工程师）

### 9.1 确认 Conda 环境已创建

```bash
conda activate bikeSharing
# 环境已包含 jupyter, numpy, scipy, pandas, matplotlib, seaborn, librosa, scikit-learn
```

### 9.2 启动 Jupyter

```bash
cd ml
jupyter notebook
```

浏览器自动打开 `http://localhost:8888`。

### 9.3 运行数据探索笔记

1. 在 Jupyter 界面中打开 `notebooks/01_data_exploration.ipynb`
2. 依次运行所有 Cell（Kernel → Restart & Run All）
3. 验证输出：
   - 正常骑行和偏摆骑行的加速度时序图
   - 两种骑行的 FFT 频谱对比图（偏摆数据在 3Hz 处有明显峰值）

预计耗时：2-3 分钟

---

## 10. 停止服务

```bash
# 停止后端（在运行 uvicorn 的终端按 Ctrl+C）

# 停止基础设施
docker-compose down
# 如果还想同时删除数据库数据（重置所有数据）
docker-compose down -v
```

---

## 11. 常见问题排查

### Q1: `docker-compose up -d` 报端口冲突

**错误信息：** `port is already allocated`

**原因：** 5432（PostgreSQL）或 6379（Redis）端口被占用。

**解决：**
```bash
# 查看占用端口的进程
netstat -ano | findstr "5432"
netstat -ano | findstr "6379"

# 如果本地已有 PostgreSQL 在运行，先停止它
# 或在 docker-compose.yml 中修改端口映射为 5433:5432 和 6380:6379
```

### Q2: Conda 环境创建失败

**错误信息：** `ResolvePackageNotFound` 或下载中断

**解决：**
```bash
# 1. 更新 conda
conda update -n base conda

# 2. 清理缓存后重试
conda clean --all
conda env create -f environment.yml

# 3. 如果下载慢，配置国内镜像（清华源）
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes
```

### Q3: bcrypt / passlib 报错

**错误信息：** `ValueError: password cannot be longer than 72 bytes` 或 `AttributeError: module 'bcrypt' has no attribute '__about__'`

**原因：** bcrypt >= 4.1 与 passlib 1.7.4 不兼容。

**解决（在 conda 环境已修复，若手动安装遇到）：**
```bash
pip install "bcrypt<4"
# 确认版本
pip show bcrypt  # Version: 3.2.2
```

### Q4: JWT Token 验证失败

**错误信息：** `jose.exceptions.JWTClaimsError: Subject must be a string.`

**原因：** python-jose 3.x 要求 JWT `sub` claim 为字符串。

**解决：** 已修复（将 `sub` 转为 `str(user["id"])`）。如果仍出现，检查 `backend/app/api/auth.py` 中 `create_access_token` 调用是否使用了 `str()`。

### Q5: 后端启动后 API 返回 401

**原因：** 使用了错误的 Token 或 Token 已过期。

**解决：**
1. 重新调用 `/api/auth/login` 获取新 Token
2. 确认 Token 在请求头中的格式为 `Authorization: Bearer <token>`（注意中间有空格）
3. 检查服务器是否重启过（内存存储会丢失所有用户数据，需重新注册）

### Q6: 移动端连不上后端

**可能原因和解决：**

| 原因 | 验证方法 | 解决 |
|------|---------|------|
| 手机和电脑不在同一网络 | 检查手机 IP 和电脑 IP 前 3 段是否相同 | 连接同一 WiFi |
| 防火墙阻止 | 临时关闭 Windows 防火墙测试 | 添加防火墙入站规则允许 8000 端口 |
| `EXPO_PUBLIC_API_URL` 未设置 | `echo $EXPO_PUBLIC_API_URL` | 设置为电脑局域网 IP |
| 后端未监听 0.0.0.0 | `netstat -ano \| findstr "8000"` | uvicorn 加 `--host 0.0.0.0` |

### Q7: Docker 镜像拉取慢

配置镜像加速器（国内环境）：

```json
// Docker Desktop → Settings → Docker Engine → 编辑配置
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
```

### Q8: `npm install` 失败

```bash
# 清除 npm 缓存重试
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# 或使用国内镜像
npm install --registry=https://registry.npmmirror.com
```

### Q9: 传感器在真机上不工作

Expo Go 中的传感器权限：

- **iOS：** 首次使用传感器时系统会弹出权限请求，必须点击"允许"。如果点错了，到 设置 → 隐私 → 运动与健身 中开启。
- **Android：** 权限在 `app.json` 中已声明（`RECORD_AUDIO`, `ACCESS_FINE_LOCATION`, `ACTIVITY_RECOGNITION`），安装时自动授予。

### Q10: 项目启动后什么端点能用？

| 端点 | 状态 | 说明 |
|------|------|------|
| `GET /api/health` | ✅ | 随时可用 |
| `POST /api/auth/register` | ✅ | 随时可用 |
| `POST /api/auth/login` | ✅ | 随时可用 |
| `GET /api/auth/me` | ✅ | 需要 Token |
| `POST /api/detection/wheel-wobble/{id}` | ✅ | 需要 Token |
| `POST /api/detection/chain-noise/{id}` | ✅ | 需要 Token |
| `POST /api/detection/handlebar/{id}` | ✅ | 需要 Token |
| `POST /api/rides/start` | ⚠️ Stub | 返回模拟数据 |
| `POST /api/rides/{id}/end` | ⚠️ Stub | 返回模拟数据 |
| `GET /api/rides/` | ⚠️ Stub | 返回空列表 |
| `GET /api/detection/report/{id}` | ⚠️ Stub | 返回空报告 |

---

## 12. 完整启动检查清单

一键复制粘贴验证整套系统：

```bash
# === 基础设施 ===
docker info > /dev/null 2>&1 && echo "✅ Docker 运行中" || echo "❌ Docker 未启动"
docker-compose ps | grep -q healthy && echo "✅ PostgreSQL + Redis 健康" || echo "❌ 容器异常"

# === 后端环境 ===
conda activate bikeSharing 2>/dev/null && echo "✅ Conda 环境就绪" || echo "❌ Conda 环境未创建"
python -c "import fastapi, numpy, scipy, librosa" 2>/dev/null && echo "✅ Python 依赖完整" || echo "❌ 缺少依赖"

# === 后端服务 ===
curl -s http://localhost:8000/api/health | grep -q ok && echo "✅ 后端服务运行中" || echo "❌ 后端未启动"

# === 测试 ===
cd backend && pytest -q 2>/dev/null && echo "✅ 测试全部通过" || echo "❌ 测试有失败"

# === 移动端 ===
cd ../mobile && [ -d node_modules ] && echo "✅ 移动端依赖已安装" || echo "❌ 需要 npm install"
```
