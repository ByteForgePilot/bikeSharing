# 10 — 开发协作流程

## 概述

项目使用 Git + GitHub 进行版本控制和团队协作。每个人在自己的分支上开发，
通过 Pull Request 合并到 main 分支。

---

## 预备：克隆仓库

```bash
git clone https://github.com/ByteForgePilot/bikeSharing.git
cd bikeSharing
```

如果你是刚加入的协作者，先让 Owner 在 Settings → Collaborators 中添加你的 GitHub 用户名。

---

## 环境搭建

### 后端/算法工程师

```bash
# Conda（推荐）
conda env create -f environment.yml
conda activate bikeSharing

# 启动基础设施
docker-compose up -d db redis

# 启动后端
cd backend
uvicorn app.main:app --reload
```

### 移动端工程师

```bash
cd mobile
npm install
npx expo start
```

---

## Git 工作流

```
main ───●──────────●──────────●──────────●
         \          \          \          \
feature/a ●──●──●    \          \          \
                     feature/b  ●──●──●    \
                                  feature/c ●──●
                                              \
                                          PR → main
```

### 第一步：从 main 创建功能分支

```bash
git checkout main
git pull origin main
git checkout -b feature/你的功能名
```

分支命名规范：
- `feature/` — 新功能（如 `feature/fft-analysis`, `feature/login-ui`）
- `fix/` — Bug 修复（如 `fix/jwt-expire`, `fix/sensor-crash`）
- `docs/` — 文档更新
- `refactor/` — 代码重构

### 第二步：开发

在分支上正常开发，频繁小步提交：

```bash
git add <具体文件>      # 不要 git add . （避免误提交 .env 等敏感文件）
git commit -m "做了什么，为什么这样做"
```

**Commit 风格：**
- 中文或英文均可，保持一致
- 标题简洁（< 50 字），正文可以详细
- 好例子：`修复 JWT sub 必须为字符串，python-jose 3.x 要求`
- 坏例子：`fix` / `update` / `.`

### 第三步：提交前运行测试

```bash
cd backend && pytest    # 26 个测试应全部通过
```

### 第四步：推送并创建 PR

```bash
git push -u origin feature/你的功能名
# 然后在 GitHub 网页上创建 Pull Request
```

### 第五步：Code Review

- 至少 1 人 Review 后方可合并
- Review 者关注：逻辑正确性、测试覆盖、代码风格
- 如果有 CI 检查失败，先修 CI

### 第六步：合并后清理

```bash
git checkout main
git pull origin main
git branch -d feature/你的功能名    # 删除本地分支
git push origin --delete feature/你的功能名  # 删除远程分支（或通过 PR 页面按钮）
```

---

## Git 注意事项

### 永远不要做的事

- ❌ `git push --force` 到 main 分支
- ❌ 提交 `.env` 文件（包含密钥）
- ❌ 提交 `node_modules`、`__pycache__`、`.pytest_cache`
- ❌ `git add .` 或 `git add -A`（容易误加上述文件）

### 遇到冲突

```bash
git checkout main && git pull
git checkout feature/你的分支
git merge main        # 或 git rebase main
# 解决冲突...
git add .
git commit -m "合并 main 的更新"
```

---

## 环境管理

### Conda 环境更新

当 `environment.yml` 有变更时（有人添加了新依赖）：

```bash
conda env update -f environment.yml --prune
```

- `--prune` 会移除环境中多余的包，与 `environment.yml` 完全保持一致

### 导出当前环境

如果在自己环境做了调试验证后想分享给队友：

```bash
conda env export -n bikeSharing > environment.yml
# 注意：这会写入平台和版本号信息，Windows/Mac/Linux 间可能不兼容
```

---

## 敏感配置处理

`SECRET_KEY`、数据库密码等敏感信息不应出现在代码中。

```bash
# 后端：创建 .env 文件（已在 .gitignore 中）
cd backend
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env
```

---

## 角色与关注文档

| 角色 | 必读文档 |
|------|---------|
| 后端工程师 | 01-架构, 02-API, 03-数据库, 04-算法, 08-部署, 09-测试, 10-协作 |
| 移动端工程师 | 01-架构, 02-API, 05-传感器, 06-移动端, 10-协作 |
| 算法工程师 | 01-架构, 04-算法, 05-传感器, 07-ML, 09-测试 |

---

## IDE 推荐配置

### VS Code 扩展

- Python: `ms-python.python`, `ms-python.vscode-pylance`
- React Native: `msjsdiag.vscode-react-native`
- Git: `eamodio.gitlens`
- Docker: `ms-azuretools.vscode-docker`
- Jupyter: `ms-toolsai.jupyter`

### 自动格式化

```json
// .vscode/settings.json
{
  "[python]": { "editor.defaultFormatter": "ms-python.black-formatter" },
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[typescriptreact]": { "editor.defaultFormatter": "esbenp.prettier-vscode" }
}
```

---

## 常见问题

### Q: `pip install` 速度慢

使用清华镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: Docker 拉取镜像慢

配置 Docker 镜像加速器（阿里云容器镜像服务），
或在 `docker-compose.yml` 中已使用的镜像事先 `docker pull`。

### Q: Expo 连接不到开发服务器

1. 确保手机和电脑在同一局域网
2. 检查防火墙是否阻止了 19000/19001/19002 端口
3. 运行 `npx expo start --tunnel` 使用隧道模式

### Q: 测试中出现 bcrypt/passlib 错误

确保 `bcrypt<4` 已安装：
```bash
pip install "bcrypt<4"
```
（environment.yml 中已固定版本）

### Q: 数据库连接失败

```bash
# 确认 Docker 服务在运行
docker ps

# 确认 PostgreSQL 健康
docker-compose exec db pg_isready -U postgres

# 如果容器不存在，重新创建
docker-compose up -d db
```
