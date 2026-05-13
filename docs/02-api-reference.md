# 02 — API 完整参考

Base URL: `http://localhost:8000/api`

## 认证说明

除特别标注外，所有接口需在请求头携带 Bearer Token：

```
Authorization: Bearer <access_token>
```

Token 通过 `/api/auth/login` 获取，默认 60 分钟过期，HS256 签名。

**Token Payload 结构：**
```json
{
  "sub": "1",           // 用户 ID (字符串)
  "username": "testuser",
  "exp": 1715678901     // 过期时间 (Unix timestamp)
}
```

---

## 1. 系统

### `GET /api/health`

健康检查，无需认证。

**响应 200:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## 2. 认证 (Auth)

### `POST /api/auth/register`

注册新用户。无需认证。

**请求体 (JSON):**
```json
{
  "username": "testuser",
  "password": "testpass"
}
```

**响应 200:**
```json
{
  "id": 1,
  "username": "testuser"
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 400 | 用户名已存在 |

---

### `POST /api/auth/login`

登录获取访问令牌。使用 OAuth2 表单格式（`application/x-www-form-urlencoded`）。

**请求体 (Form):**
```
username=testuser&password=testpass
```

**响应 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 401 | 用户名或密码错误 |

---

### `GET /api/auth/me`

获取当前用户信息。

**请求头:**
```
Authorization: Bearer <access_token>
```

**响应 200:**
```json
{
  "id": 1,
  "username": "testuser"
}
```

**错误:**
| 状态码 | 说明 |
|--------|------|
| 401 | Token 无效或已过期 |

---

## 3. 骑行管理 (Rides)

> 所有 rides 端点已通过 SQLAlchemy AsyncSession 接入 PostgreSQL，数据持久化存储。

### `POST /api/rides/start`

开始一次骑行。

**查询参数:**
| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `bike_id` | string | — | 是 | 单车编号 |
| `lat` | float | 0.0 | 否 | 起始纬度 |
| `lng` | float | 0.0 | 否 | 起始经度 |

**响应 200:**
```json
{
  "ride": {
    "id": 1,
    "user_id": "1",
    "bike_id": "BIKE-001",
    "start_lat": 30.5,
    "start_lng": 104.1,
    "started_at": "2026-05-13T12:00:00Z",
    "status": "active"
  },
  "message": "Ride started"
}
```

---

### `POST /api/rides/{ride_id}/end`

结束骑行并触发故障分析。

**路径参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `ride_id` | int | 骑行记录 ID |

**查询参数:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lat` | float | 0.0 | 结束纬度 |
| `lng` | float | 0.0 | 结束经度 |

**响应 200:**
```json
{
  "ride_id": 1,
  "status": "completed",
  "message": "Ride ended, analysis queued"
}
```

---

### `POST /api/rides/{ride_id}/sensor-data`

上传传感器批量数据。

**路径参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `ride_id` | int | 骑行记录 ID |

**请求体 (JSON):**
```json
{
  "accelerometer": [
    {"x": 0.12, "y": 0.05, "z": 9.81, "timestamp": 0.0}
  ],
  "gyroscope": [
    {"x": 0.01, "y": 0.02, "z": 0.00, "timestamp": 0.0}
  ],
  "sample_rate": 50.0
}
```

**响应 200:**
```json
{
  "status": "received",
  "samples": 50,
  "ride_id": 1
}
```

---

### `POST /api/rides/{ride_id}/audio`

上传音频片段。接收原始音频数据供后续 MFCC 特征提取。

**响应 200:**
```json
{
  "status": "received",
  "ride_id": 1
}
```

---

### `GET /api/rides/`

获取用户骑行历史列表。

**查询参数:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 20 | 返回数量上限 |
| `offset` | int | 0 | 分页偏移 |

**响应 200:**
```json
{
  "rides": [
    {
      "id": 1,
      "user_id": 1,
      "bike_id": "BIKE-001",
      "start_lat": 30.5,
      "start_lng": 104.1,
      "end_lat": null,
      "end_lng": null,
      "started_at": "2026-05-13T12:00:00+00:00",
      "ended_at": null,
      "status": "active"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### `GET /api/rides/{ride_id}`

获取单次骑行详情。仅返回当前用户自己的骑行记录（其他人返回 404）。

**响应 200:**
```json
{
  "id": 1,
  "user_id": 1,
  "bike_id": "BIKE-001",
  "start_lat": 30.5,
  "start_lng": 104.1,
  "end_lat": null,
  "end_lng": null,
  "started_at": "2026-05-13T12:00:00+00:00",
  "ended_at": null,
  "status": "active"
}
```

---

## 4. 故障检测 (Detection)

### `POST /api/detection/wheel-wobble/{ride_id}`

轮胎偏摆检测。分析加速度计数据中的周期性振动。

**路径参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `ride_id` | int | 骑行记录 ID |

**请求体 (JSON) — WheelWobbleRequest:**
```json
{
  "accelerometer_data": [
    {"x": 0.12, "y": 0.05, "z": 9.81, "timestamp": 0.0},
    {"x": 0.15, "y": 0.04, "z": 9.79, "timestamp": 0.02}
  ],
  "sample_rate": 50.0
}
```

**响应 200:**
```json
{
  "ride_id": 1,
  "wheel_wobble": {
    "detected": "suspect",
    "confidence": 0.65,
    "detail": "RMS vibration: 0.180 m/s^2 (threshold: 0.3)"
  }
}
```

**返回字段说明:**
| 字段 | 类型 | 取值 |
|------|------|------|
| `detected` | string | `normal` / `suspect` / `fault` / `unknown` |
| `confidence` | float | 0.0 ~ 1.0（0 表示完全不确定，1 表示完全确定） |
| `detail` | string | 人类可读的诊断详情 |

---

### `POST /api/detection/chain-noise/{ride_id}`

链条异响检测。分析音频特征向量中的异常模式。

**请求体 (JSON) — ChainNoiseRequest:**
```json
{
  "audio_features": [0.12, 0.08, 0.15, 0.11, 0.09]
}
```

**响应 200:**
```json
{
  "ride_id": 1,
  "chain_noise": {
    "detected": "normal",
    "confidence": 0.82,
    "detail": "Anomaly score: 0.183 (mean=0.110, std=0.026)"
  }
}
```

---

### `POST /api/detection/handlebar/{ride_id}`

车头不正检测。分析陀螺仪偏航角数据中的系统偏移。

**请求体 (JSON) — HandlebarRequest:**
```json
{
  "gyroscope_data": [
    {"x": 0.01, "y": 0.02, "z": 0.05, "timestamp": 0.0},
    {"x": 0.01, "y": 0.01, "z": 0.04, "timestamp": 0.02}
  ],
  "sample_rate": 50.0
}
```

**响应 200:**
```json
{
  "ride_id": 1,
  "handlebar_misalignment": {
    "detected": "fault",
    "confidence": 0.75,
    "detail": "Mean yaw offset: 5.20° (threshold: 3.0°)"
  }
}
```

---

### `GET /api/detection/report/{ride_id}`

获取一次骑行的综合检测报告（当前返回空结果，待实现检测结果持久化）。

**响应 200:**
```json
{
  "ride_id": 1,
  "wheel_wobble": null,
  "chain_noise": null,
  "handlebar_misalignment": null,
  "overall_status": "pending"
}
```

---

## 5. Pydantic Schema 参考

### SensorSample
```python
class SensorSample(BaseModel):
    x: float
    y: float
    z: float
    timestamp: float
```

### WheelWobbleRequest
```python
class WheelWobbleRequest(BaseModel):
    accelerometer_data: List[SensorSample]
    sample_rate: float = 50.0
```

### HandlebarRequest
```python
class HandlebarRequest(BaseModel):
    gyroscope_data: List[SensorSample]
    sample_rate: float = 50.0
```

### ChainNoiseRequest
```python
class ChainNoiseRequest(BaseModel):
    audio_features: List[float]
```

### SensorBatch（已定义，与 rides.py 中 SensorDataUpload 一致）
```python
class SensorBatch(BaseModel):
    ride_id: int
    accelerometer: List[SensorSample] = []
    gyroscope: List[SensorSample] = []
    sample_rate: float = 50.0
```

### AudioSegment（已定义，未使用）
```python
class AudioSegment(BaseModel):
    ride_id: int
    sample_rate: int = 44100
    duration: float
    features: List[float] = []
```

### FaultDetectionResult（已定义，未使用）
```python
class FaultDetectionResult(BaseModel):
    ride_id: int
    wheel_wobble: Optional[dict] = None
    chain_noise: Optional[dict] = None
    handlebar_misalignment: Optional[dict] = None
    overall_status: str = "pending"
```

---

## 6. API 路由总表

| 方法 | 完整路径 | 认证 | 状态 |
|------|---------|------|------|
| GET | `/api/health` | 否 | ✅ 实现 |
| POST | `/api/auth/register` | 否 | ✅ 实现 |
| POST | `/api/auth/login` | 否 | ✅ 实现 |
| GET | `/api/auth/me` | Bearer | ✅ 实现 |
| POST | `/api/rides/start` | Bearer | ✅ 实现 |
| POST | `/api/rides/{id}/end` | Bearer | ✅ 实现 |
| POST | `/api/rides/{id}/sensor-data` | Bearer | ✅ 实现 |
| POST | `/api/rides/{id}/audio` | Bearer | ✅ 实现 |
| GET | `/api/rides/` | Bearer | ✅ 实现 |
| GET | `/api/rides/{id}` | Bearer | ✅ 实现 |
| POST | `/api/detection/wheel-wobble/{id}` | Bearer | ✅ 实现 |
| POST | `/api/detection/chain-noise/{id}` | Bearer | ✅ 实现 |
| POST | `/api/detection/handlebar/{id}` | Bearer | ✅ 实现 |
| GET | `/api/detection/report/{id}` | Bearer | ⚠️ Stub |

---

## 7. 通用错误响应

### 401 Unauthorized
```json
{
  "detail": "Invalid token"
}
```
或
```json
{
  "detail": "Invalid credentials"
}
```

### 422 Unprocessable Entity
当请求体不符合 Pydantic Schema 时返回，包含详细校验错误：
```json
{
  "detail": [
    {
      "loc": ["body", "accelerometer_data"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 400 Bad Request
```json
{
  "detail": "Username already exists"
}
```
