# 开发环境配置手册

> 最后更新: 2026-05-13  
> 操作系统: Windows 11 Home China (x86_64)  
> 内存: 16GB

---

## 磁盘布局

| 盘 | 类型 | 容量 | 已用 | 可用 | 用途 |
|----|------|------|------|------|------|
| C | SSD | 201G | 158G | 43G (21%) | 系统 + 用户数据 |
| D | SSD | 500G | 140G | 361G (72%) | **开发工具 / 应用** |
| E | SSD | 200G | 34G | 167G (83%) | **项目代码 / MySQL** |
| F | SSD | 52G | 0.2G | 52G | 暂空 |

---

## 各语言/工具版本与路径

### Python (conda)

**基础环境**: Miniforge3 @ `D:\miniforge3`  
**自定义环境目录**: `D:\conda_envs`  
**包缓存**: `D:\conda_pkgs` (26GB)  
**配置文件**: `C:\Users\Sherlock\.condarc`

```yaml
channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
  - conda-forge
envs_dirs:
  - D:\conda_envs
pkgs_dirs:
  - D:\conda_pkgs
```

| 环境名 | 路径 | 用途 |
|--------|------|------|
| base | D:\miniforge3 | 系统默认 Python 3.12.12 |
| bikeSharing | D:\conda_envs\bikeSharing | **共享单车项目 (FastAPI + ML)** |
| AIGC | D:\conda_envs\AIGC | AI 生成内容 |
| NUAA-course-skills | D:\conda_envs\NUAA-course-skills | 课程技能 |
| PatReg | D:\conda_envs\PatReg | 专利注册 |
| cat_cafe_env | D:\conda_envs\cat_cafe_env | 猫咖项目 |
| homework | D:\conda_envs\homework | 作业 |
| py311 | D:\conda_envs\py311 | Python 3.11 |
| uv_env | D:\conda_envs\uv_env | UV 测试环境 |

### Node.js

**版本管理器**: 无 (fnm/nvm-windows 被 GFW 拦截)  
**替代方案**: 双版本并存，按 PATH 优先级切换

| 版本 | 路径 | 用途 |
|------|------|------|
| v22.21.1 (LTS) | `D:\node-22` | **默认** — 适合 Expo/React Native |
| v24.15.0 | `D:\nodejs` | 备用 |

**切换版本**: 改 User PATH 中 `D:\node-22` 和 `D:\nodejs` 的先后顺序  
**npm 全局目录**: `C:\Users\Sherlock\AppData\Roaming\npm`  
**npm 源**: `https://registry.npmmirror.com` (淘宝镜像)  
**配置文件**: `C:\Users\Sherlock\.npmrc`

### Java

| 版本 | 路径 | 用途 |
|------|------|------|
| JDK 21.0.11 (Temurin) | `D:\Java\jdk-21.0.11+10` | 老项目兼容 |
| JDK 17.0.19 (Temurin) | `D:\Java\jdk-17\jdk-17.0.19+10` | **Android APK 构建** (React Native 要求) |
| JRE 1.8.0_491 | `C:\Program Files\Java\jre1.8.0_491` | 老应用兼容 (仅 java) |

**JDK 17 bin**: 不在 PATH 中，Android Studio 内通过 Gradle JDK 设置指向

### C/C++

| 工具 | 路径 | 版本 |
|------|------|------|
| CMake | `D:\Cmake\bin` | 4.2.0 |
| GCC (MSYS2) | MSYS2 shell 内可用 | — |

### 数据库

| 工具 | 路径 | 版本/状态 |
|------|------|----------|
| MySQL | `E:\mysql-8.0.45-winx64\bin` | 8.0.45 |
| PostgreSQL | Docker: `postgres:16-alpine` (端口 5432) | ✅ 运行中 |
| Redis | Docker: `redis:7-alpine` (端口 6379) | ✅ 运行中 |

### 基础设施（Docker）

| 容器 | 镜像 | 端口 | 状态 |
|------|------|------|------|
| bikesharing-db-1 | postgres:16-alpine | 5432 | ✅ healthy |
| bikesharing-redis-1 | redis:7-alpine | 6379 | ✅ healthy |

启动命令：`docker compose up -d db redis`

### Android

| 工具 | 路径 | 版本/状态 |
|------|------|----------|
| Android Studio | `D:\Android Studio` | 2025.3.4 |
| Android SDK | `D:\Android\Sdk` | API 34 |
| JDK 17 (Temurin) | `D:\Java\jdk-17\jdk-17.0.19+10` | APK 构建专用 |

> Android Studio → File → Settings → Build Tools → Gradle → Gradle JDK 设置为 JDK 17

### 其他工具

| 工具 | 路径 | 版本 |
|------|------|------|
| Git | `D:\Git` | 2.52.0 |
| VS Code | `D:\Microsoft VS Code` | — |
| Chocolatey | `C:\ProgramData\chocolatey` | — |
| GitHub CLI | `D:\GitHub CLI` | — |
| Expo CLI | npx expo | 0.22.28 |

---

## PATH 配置

### User PATH (已精简，17 条)

```
 1. D:\node-22                         ← 默认 Node 22 LTS
 2. C:\Users\Sherlock\bin
 3. D:\Git\mingw64\bin
 4. D:\Git\usr\local\bin
 5. D:\Git\usr\bin
 6. D:\miniforge3                      ← conda base
 7. D:\miniforge3\Library\mingw-w64\bin
 8. D:\miniforge3\Library\usr\bin
 9. D:\miniforge3\Library\bin
10. D:\miniforge3\Scripts
11. D:\miniforge3\bin
12. D:\miniforge3\condabin
13. D:\Java\jdk-21.0.11+10\bin         ← JDK 21 (javac)
14. E:\mysql-8.0.45-winx64\bin         ← MySQL
15. C:\Users\Sherlock\AppData\Roaming\npm
16. D:\Git\usr\bin\vendor_perl
17. D:\Git\usr\bin\core_perl
```

### System PATH (19 条 — 不改动)

含系统目录、CMake、Git cmd、Node v24、Chocolatey、GitHub CLI 等。

---

## 恢复/修复脚本

所有脚本位于 `E:\Project\bikeSharing\scripts\`:

| 脚本 | 用途 | 权限 |
|------|------|------|
| `enable_wsl.ps1` | 启用 WSL + 虚拟机平台 | 管理员 |
| `wsl_import.ps1` | 导入 Ubuntu 22.04 到 WSL | 管理员 |
| `clean_system_path.ps1` | 清理 System PATH 死链接 | 管理员 |
| `restore_system_path.ps1` | 紧急恢复 System PATH | 管理员 |
| `move_pagefile.ps1` | 虚拟内存从 C 移到 D | 管理员 |

---

## 已完成项目

- [x] **重启电脑** — WSL 功能已启用生效
- [x] **管理员运行 `wsl_import.ps1`** — Ubuntu 已导入 WSL
- [x] **安装 Docker Desktop** — Docker 29.4.3 + Compose v5.1.3
- [x] **`docker compose up -d db redis`** — PostgreSQL + Redis 运行中
- [x] **数据库表已创建** — users / rides / fault_reports
- [x] **32 个测试全部通过** — 3 API + 23 服务层 + 6 数据库集成
- [ ] 管理员运行 `move_pagefile.ps1` — C 盘还能释放 13GB
