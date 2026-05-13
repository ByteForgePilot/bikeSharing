# 03 — 数据库设计

## 概述

使用 PostgreSQL 16 作为主存储。ORM 模型已通过 SQLAlchemy 2.0 AsyncSession 接入路由，
Auth（注册/登录/JWT）和 Rides（CRUD）均已持久化，32 个测试全部通过。

---

## ER 图

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│     users         │         │      rides        │         │  fault_reports    │
├──────────────────┤         ├──────────────────┤         ├──────────────────┤
│ PK id       INT  │──┐      │ PK id       INT  │──┐      │ PK id       INT  │
│    username  STR │  │      │ FK user_id  INT  │◄─┘      │ FK ride_id  INT  │◄─┐
│    password_     │  │      │    bike_id   STR │         │    wheel_wobble_  │  │
│      hash    STR │  │      │    start_lat FLT │         │      detected STR │  │
│    created_at DT │  │      │    start_lng FLT │         │    wheel_wobble_  │  │
└──────────────────┘  │      │    end_lat   FLT │         │      confidence FLT│  │
                      └─────►│    end_lng   FLT │         │    wheel_wobble_  │  │
                             │    started_at DT │         │      detail   TXT │  │
                             │    ended_at   DT │         │    chain_noise_   │  │
                             │    status    STR │         │      detected STR │  │
                             └──────────────────┘         │    chain_noise_   │  │
                                                          │      confidence FLT│  │
                                                          │    chain_noise_   │  │
                                                          │      detail   TXT │  │
                                                          │    handlebar_     │  │
                                                          │      detected STR │  │
                                                          │    handlebar_     │  │
                                                          │      confidence FLT│  │
                                                          │    handlebar_     │  │
                                                          │      detail   TXT │  │
                                                          │    created_at DT │  │
                                                          └──────────────────┘  │
                                                                                │
    users.id ────────► rides.user_id (1:N)                                      │
    rides.id ────────► fault_reports.ride_id (1:N) ─────────────────────────────┘
```

---

## DDL（等效 SQL）

```sql
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users (username);

CREATE TABLE rides (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    bike_id     VARCHAR(64) NOT NULL,
    start_lat   DOUBLE PRECISION DEFAULT 0.0,
    start_lng   DOUBLE PRECISION DEFAULT 0.0,
    end_lat     DOUBLE PRECISION,
    end_lng     DOUBLE PRECISION,
    started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at    TIMESTAMP,
    status      VARCHAR(20) DEFAULT 'active'  -- active | completed | cancelled
);

CREATE INDEX idx_rides_user_id ON rides (user_id);
CREATE INDEX idx_rides_bike_id ON rides (bike_id);
CREATE INDEX idx_rides_status ON rides (status);

CREATE TABLE fault_reports (
    id                         SERIAL PRIMARY KEY,
    ride_id                    INTEGER NOT NULL REFERENCES rides(id),
    wheel_wobble_detected      VARCHAR(20) DEFAULT 'unknown',  -- normal | suspect | fault | unknown
    wheel_wobble_confidence    DOUBLE PRECISION,
    wheel_wobble_detail        TEXT,
    chain_noise_detected       VARCHAR(20) DEFAULT 'unknown',
    chain_noise_confidence     DOUBLE PRECISION,
    chain_noise_detail         TEXT,
    handlebar_detected         VARCHAR(20) DEFAULT 'unknown',
    handlebar_confidence       DOUBLE PRECISION,
    handlebar_detail           TEXT,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fault_reports_ride_id ON fault_reports (ride_id);
```

---

## ORM 模型 (SQLAlchemy)

### Base

```python
# backend/app/models/__init__.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### User

```python
# backend/app/models/user.py
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    created_at    = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    rides = relationship("Ride", back_populates="user")
```

### Ride

```python
# backend/app/models/ride.py
class Ride(Base):
    __tablename__ = "rides"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    bike_id    = Column(String(64), nullable=False, index=True)
    start_lat  = Column(Float, default=0.0)
    start_lng  = Column(Float, default=0.0)
    end_lat    = Column(Float, nullable=True)
    end_lng    = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    ended_at   = Column(DateTime(timezone=True), nullable=True)
    status     = Column(String(20), default="active")

    user          = relationship("User", back_populates="rides")
    fault_reports = relationship("FaultReport", back_populates="ride")
```

### FaultReport

```python
# backend/app/models/fault_report.py
class FaultReport(Base):
    __tablename__ = "fault_reports"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    ride_id                 = Column(Integer, ForeignKey("rides.id"), nullable=False)
    wheel_wobble_detected   = Column(String(20), default="unknown")
    wheel_wobble_confidence = Column(Float, nullable=True)
    wheel_wobble_detail     = Column(Text, nullable=True)
    chain_noise_detected    = Column(String(20), default="unknown")
    chain_noise_confidence  = Column(Float, nullable=True)
    chain_noise_detail      = Column(Text, nullable=True)
    handlebar_detected      = Column(String(20), default="unknown")
    handlebar_confidence    = Column(Float, nullable=True)
    handlebar_detail        = Column(Text, nullable=True)
    created_at              = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    ride = relationship("Ride", back_populates="fault_reports")
```

---

## 索引策略

| 表 | 索引 | 类型 | 目的 |
|----|------|------|------|
| `users` | `username` | UNIQUE B-tree | 登录查询 + 唯一约束 |
| `rides` | `user_id` | B-tree | 查询用户历史骑行 |
| `rides` | `bike_id` | B-tree | 按单车查询骑行记录 |
| `rides` | `status` | B-tree | 筛选进行中/已完成骑行 |
| `fault_reports` | `ride_id` | B-tree | 按骑行查检测报告 |

---

## 表关系

| 关系 | 类型 | 外键 |
|------|------|------|
| User → Ride | 1:N | `rides.user_id` → `users.id` |
| Ride → FaultReport | 1:N | `fault_reports.ride_id` → `rides.id` |

级联策略使用 SQLAlchemy 默认值（无自动级联删除）。

---

## Docker Compose 配置

```yaml
db:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: bikesharing
  ports:
    - "5432:5432"
  volumes:
    - pgdata:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 3s
    retries: 5
```

连接字符串：
```
async:  postgresql+asyncpg://postgres:postgres@localhost:5432/bikesharing
sync:   postgresql://postgres:postgres@localhost:5432/bikesharing
```

---

## 迁移计划（Alembic）

当前尚未初始化 Alembic。后续步骤：

```bash
cd backend
alembic init alembic
# 编辑 alembic/env.py 导入 Base 和 config
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## 待讨论事项

1. **FaultReport 表结构** — 当前使用三个独立的 `detected/confidence/detail` 列组。
   如果未来增加第 4 种故障类型，需要 ALTER TABLE。替代方案：使用 JSONB 列 `faults JSONB` 将检测结果存储为灵活文档。
   **建议**：项目初期保持当前结构（简单直观），如果故障类型超过 5 种再迁移。

2. **骑行轨迹存储** — 当前 `start_lat/lng` 和 `end_lat/lng` 仅存储起终点。
   如果后续需要完整轨迹，可以添加 `ride_locations` 表或使用 PostGIS 扩展。

3. **Redis** — 当前已启动（Docker），尚未在应用层使用。计划用途：会话缓存、检测任务队列。
