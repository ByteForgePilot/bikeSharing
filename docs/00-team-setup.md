# 00 — 团队零基础配置指南

> 面向从未接触过本项目的队友。每一步都附带验证命令和国内镜像加速方案。
> 预计耗时：**60-90 分钟**（取决于网络速度）。

---

## 前提条件

- Windows 10/11 64 位（macOS 也可，本指南以 Windows 为主）
- 电脑内存 ≥ 8GB（Docker 需要）
- 电脑硬盘剩余空间 ≥ 20GB（Conda 环境 + Docker 镜像）
- 有一个 GitHub 账号

---

## Step 1: 安装 Git

Git 是代码版本管理工具，用来拉取项目代码。

### 安装

```bash
winget install Git.Git
```

如果没有 winget，去 [Git 官网](https://git-scm.com/download/win) 下载安装包。
> 官网下载慢可去 [淘宝镜像](https://registry.npmmirror.com/binary.html?path=git-for-windows/) 下载最新版本。

安装时全用默认选项即可。

### 验证

打开 **PowerShell** 或 **Git Bash**：

```bash
git --version
# 预期输出: git version 2.4x.x
```

---

## Step 2: 安装 Miniforge3（Conda 环境管理器）

项目用 Conda 管理 Python 环境，所有依赖统一在 `environment.yml` 中维护。

### 安装

```bash
winget install CondaForge.Miniforge3
```

> 如果 winget 不可用，去 [Miniforge GitHub](https://github.com/conda-forge/miniforge/releases) 下载 `Miniforge3-Windows-x86_64.exe`。
> GitHub 下载慢可以：https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/

安装时选择：
- **Install for: All Users (requires admin)**
- **安装路径: 默认 `C:\Users\<用户名>\miniforge3` 即可**
- **勾选: Add Miniforge3 to PATH**

### 配置国内镜像（清华源）

安装完成后，打开**新的** PowerShell，配置清华镜像加速：

```bash
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes
```

### 验证

```bash
conda --version
# 预期输出: conda 24.x.x 或更高
```

---

## Step 3: 安装 Docker Desktop

Docker 运行 PostgreSQL 数据库和 Redis 缓存。

### 3.1 启用 WSL 2（Windows 必需）

以**管理员身份**打开 PowerShell：

```powershell
wsl --install
```

重启电脑。

### 3.2 安装 Docker Desktop

```bash
winget install Docker.DockerDesktop
```

> 如果 winget 不可用，去 [Docker 官网](https://www.docker.com/products/docker-desktop/) 下载。
> 国内下载慢可去 [Docker 镜像站](https://docker.1ms.run) 下载 `Docker Desktop Installer.exe`。

安装时勾选 **"Use WSL 2 instead of Hyper-V"**。

### 3.3 配置 Docker 国内镜像加速器

打开 Docker Desktop → 右上角齿轮 **Settings** → **Docker Engine**，编辑 JSON 配置：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
```

点击 **Apply & Restart**。

### 验证

```bash
docker --version
# 预期输出: Docker version 27.x.x 或更高

docker compose version
# 预期输出: Docker Compose version v2.x.x 或更高

docker info
# 应该看到 Server Version 等信息，无 error
```

---

## Step 4: 安装 Node.js 22 LTS

移动端（React Native Expo）开发需要 Node.js。

### 安装

```bash
winget install OpenJS.NodeJS.LTS
```

> 如果 winget 不可用，去 [Node.js 中文网](https://nodejs.cn/download/) 下载 Windows 安装包（选择 LTS 版本）。

### 配置国内 npm 镜像（淘宝源）

```bash
npm config set registry https://registry.npmmirror.com
```

### 验证

```bash
node --version
# 预期: v22.x.x

npm --version
# 预期: 10.x.x 或更高
```

---

## Step 5: 克隆项目仓库

```bash
cd E:\Project
git clone https://github.com/ByteForgePilot/bikeSharing.git
cd bikeSharing
```

> 如果 GitHub 下载慢（几十 KB/s），用国内加速：
> ```bash
> git clone https://ghproxy.com/https://github.com/ByteForgePilot/bikeSharing.git
> ```

### 验证

```bash
ls
# 应该看到: backend/  mobile/  ml/  docs/  README.md  environment.yml  docker-compose.yml
```

---

## Step 6: 创建 Conda 环境

```bash
conda env create -f environment.yml
```

> 首次创建需下载约 200+ 个包，约 5-15 分钟。
> 如果下载中断，运行 `conda clean --all` 然后重试。
> 如果一直报网络错误，确认 Step 2 的清华镜像已配置好。

### 验证

```bash
conda activate bikeSharing
# 终端提示符前应出现 (bikeSharing)

python --version
# 预期: Python 3.11.x

python -c "import fastapi, sqlalchemy, asyncpg, numpy, scipy; print('All OK')"
# 预期: All OK
```

---

## Step 7: 启动 Docker 服务（PostgreSQL + Redis）

```bash
docker compose up -d db redis
```

首次运行会拉取 `postgres:16-alpine` 和 `redis:7-alpine` 镜像，约 3-5 分钟。

### 验证

```bash
docker compose ps
```

**预期输出**（STATUS 列应显示 "healthy"）：

```
NAME                  STATUS
bikesharing-db-1      Up (healthy)
bikesharing-redis-1   Up (healthy)
```

---

## Step 8: 启动后端并验证 API

打开**新的终端**（保持 Docker 终端开着）：

```bash
conda activate bikeSharing
cd E:\Project\bikeSharing\backend
set PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**预期输出**（最后一行）：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 验证 API（另开第三个终端）

```bash
# 1. 健康检查
curl http://localhost:8000/api/health
# 预期: {"status":"ok","version":"0.1.0"}

# 2. 注册
curl -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" -d "{\"username\":\"demo\",\"password\":\"demo1234\"}"
# 预期: {"id":1,"username":"demo"}

# 3. 登录
curl -X POST http://localhost:8000/api/auth/login -d "username=demo&password=demo1234"
# 预期: {"access_token":"eyJ...","token_type":"bearer"}

# 4. 骑行全流程
# 复制上一步的 token 替换 <TOKEN>
curl -X POST "http://localhost:8000/api/rides/start?bike_id=BIKE001" -H "Authorization: Bearer <TOKEN>"
curl -X POST "http://localhost:8000/api/rides/1/end" -H "Authorization: Bearer <TOKEN>"
curl http://localhost:8000/api/rides/ -H "Authorization: Bearer <TOKEN>"
```

> **PowerShell 用户注意**：PowerShell 的 `curl` 是别名，用 `curl.exe` 代替，或者直接用浏览器打开 `http://localhost:8000/docs` 在 Swagger UI 上手动测试。

---

## Step 9: 运行测试

```bash
conda activate bikeSharing
cd E:\Project\bikeSharing\backend
set PYTHONPATH=.
pytest -v
```

**预期输出（最后两行）**：

```
tests/test_rides_db.py::test_detection_with_ride PASSED                  [100%]
============================= 32 passed in X.XXs ==============================
```

全部 **32 个测试通过**。包括：
- 3 个 API 集成测试（health / auth / detection）
- 23 个服务层单元测试（传感器分析 / 音频分析 / 故障分类）
- 6 个数据库集成测试（骑行 CRUD / 分页 / 用户隔离 / 重复注册 / 检测联动）

> **如果测试失败**：确认 Docker 容器在运行（`docker compose ps`），确认 bikesharing_test 数据库存在（`docker compose exec db psql -U postgres -c "CREATE DATABASE bikesharing_test;"`）。

---

## Step 10: 安装移动端并配置

```bash
cd E:\Project\bikeSharing\mobile
npm install
```

约 3-5 分钟。

### 配置后端地址

手机需要连接到运行在电脑上的后端 API。

**先查电脑局域网 IP**：

```bash
ipconfig | findstr "IPv4"
# 例如输出: IPv4 Address . . . . . . . . : 192.168.1.105
```

**创建环境变量文件**：

```bash
echo EXPO_PUBLIC_API_URL=http://192.168.1.105:8000 > .env
```

（把 `192.168.1.105` 换成你的实际 IP）

> 如果只是用电脑浏览器模拟测试（不连真机），保留默认 `http://localhost:8000`，**跳过此步**。

### 启动 Expo

```bash
npx expo start
```

终端会显示二维码。

### 在手机上运行

1. 手机安装 **Expo Go**（App Store / 应用商店免费下载）
2. 手机和电脑**连接同一 WiFi**
3. Expo Go 扫码
4. App 加载完成，输入车辆编号点"开始骑行"

### 验证

- 加速度计和陀螺仪数值实时变化（仅在真机上，电脑模拟器无传感器）
- 几秒后故障检测状态更新

> **如果手机连不上**：检查防火墙是否阻止了 8000 端口。
> 到 Windows 防火墙 → 高级设置 → 入站规则 → 新建规则 → 端口 → TCP 8000 → 允许连接。

---

## Step 11（算法/数据工程师可选）: Jupyter Notebook

```bash
conda activate bikeSharing
cd E:\Project\bikeSharing\ml
jupyter notebook
```

浏览器自动打开，打开 `notebooks/` 目录下的 `.ipynb` 文件运行。

---

## 常见问题排查

### Q1: `docker compose up -d` 端口冲突

**错误**: `port is already allocated`

```bash
# 查看占用端口的进程
netstat -ano | findstr "5432"
netstat -ano | findstr "6379"
# 如果本地已有 PostgreSQL/Redis 在运行，先停止它们
```

### Q2: Docker 拉取镜像失败/超时

**原因**: Docker Hub 在国内不可达。

**解决**: 确认 Step 3.3 的镜像加速器已配置。如果已配置仍失败，手动拉取：
```bash
docker pull docker.1ms.run/postgres:16-alpine
docker tag docker.1ms.run/postgres:16-alpine postgres:16-alpine
docker pull docker.1ms.run/redis:7-alpine
docker tag docker.1ms.run/redis:7-alpine redis:7-alpine
```

### Q3: `conda env create` 下载慢或中断

```bash
# 确认清华源已配置
cat ~/.condarc

# 清理缓存后重试
conda clean --all
conda env create -f environment.yml
```

### Q4: bcrypt 报错

**错误**: `ValueError: password cannot be longer than 72 bytes` 或 `module 'bcrypt' has no attribute '__about__'`

**解决**: environment.yml 已固定 `bcrypt<4`，理论上不会出现。如果手动 pip 安装遇到：
```bash
pip install "bcrypt<4"
```

### Q5: `npm install` 失败

```bash
npm cache clean --force
npm install --registry=https://registry.npmmirror.com
```

### Q6: Windows 找不到 `curl`

PowerShell 中 `curl` 被 Invoke-WebRequest 别名覆盖：
```powershell
# 方法 1: 使用 curl.exe
curl.exe http://localhost:8000/api/health

# 方法 2: 删掉别名（仅当前会话）
Remove-Item Alias:curl -Force -ErrorAction SilentlyContinue

# 方法 3: 直接用浏览器打开 http://localhost:8000/docs 在 Swagger UI 上测试
```

### Q7: 手机连不上后端（`http://192.168.x.x:8000`）

| 可能原因 | 验证方法 | 解决方法 |
|---------|---------|---------|
| 不在同一 WiFi | 比较手机和电脑 IP 前三段 | 连接同一 WiFi |
| 防火墙阻止 | 临时关闭防火墙测试 | 添加入站规则允许 8000 端口 |
| 后端未监听 0.0.0.0 | `netstat -ano \| findstr "8000"` 看是否显示 `0.0.0.0:8000` | uvicorn 加 `--host 0.0.0.0` |
| EXPO_PUBLIC_API_URL 未设 | 检查 `mobile/.env` 是否存在 | `echo EXPO_PUBLIC_API_URL=http://你的IP:8000 > .env` |

---

## 推荐 VS Code 扩展

在 VS Code 中按 `Ctrl+Shift+X`，搜索安装：

| 扩展 ID | 用途 |
|---------|------|
| `ms-python.python` | Python 语法/调试 |
| `ms-python.vscode-pylance` | Python 类型检查 |
| `msjsdiag.vscode-react-native` | React Native 开发 |
| `eamodio.gitlens` | Git 增强 |
| `ms-azuretools.vscode-docker` | Docker 管理 |
| `ms-toolsai.jupyter` | Jupyter Notebook |

---

## 日常命令速查卡

```bash
# —— 启动工作 ——
docker compose up -d db redis          # 启动数据库
conda activate bikeSharing             # 激活 Python 环境
cd backend && uvicorn app.main:app --reload  # 启动后端

# —— 运行测试 ——
cd backend && pytest -v                # 全部 32 个测试
cd backend && pytest tests/test_api.py -v   # 仅 API 测试
cd backend && pytest tests/test_rides_db.py -v  # 仅数据库测试

# —— 移动端 ——
cd mobile && npx expo start            # 启动 Expo
cd mobile && npx tsc --noEmit          # TypeScript 类型检查

# —— 数据库查询 ——
docker compose exec db psql -U postgres -d bikesharing  # 进入 PostgreSQL
docker compose exec redis redis-cli                      # 进入 Redis

# —— 停止工作 ——
# 后端: Ctrl+C
docker compose down                     # 停止所有服务
docker compose down -v                  # 停止 + 清空数据
```

---

## 角色与关注文档

| 角色 | 必读文档 |
|------|---------|
| 后端工程师 | 00-team-setup, 01-architecture, 02-api-reference, 03-database-design, 08-devops, 09-testing |
| 移动端工程师 | 00-team-setup, 01-architecture, 02-api-reference, 05-sensor-guide, 06-mobile-development |
| 算法/数据工程师 | 00-team-setup, 01-architecture, 04-algorithms, 05-sensor-guide, 07-ml-pipeline |
