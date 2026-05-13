# API 接口文档

## Base URL

```
http://localhost:8000/api
```

## 认证

### 注册
```
POST /api/auth/register
Body: { "username": "string", "password": "string" }
```

### 登录
```
POST /api/auth/login
Body: x-www-form-urlencoded { username, password }
Response: { "access_token": "string", "token_type": "bearer" }
```

### 当前用户
```
GET /api/auth/me
Headers: Authorization: Bearer <token>
```

## 骑行

所有接口需要 `Authorization: Bearer <token>`

### 开始骑行
```
POST /api/rides/start?bike_id=BIKE-001&lat=30.5&lng=120.5
Response: { "ride": {...}, "message": "Ride started" }
```

### 结束骑行
```
POST /api/rides/{ride_id}/end?lat=30.51&lng=120.51
```

### 上传传感器数据
```
POST /api/rides/{ride_id}/sensor-data
Body: {
  "accelerometer": [{x, y, z, timestamp}, ...],
  "gyroscope": [{x, y, z, timestamp}, ...],
  "timestamps": [...]
}
```

### 上传音频片段
```
POST /api/rides/{ride_id}/audio
Body: multipart/form-data { audio_file }
```

### 骑行列表
```
GET /api/rides/?limit=20&offset=0
```

## 故障检测

### 轮胎偏摆检测
```
POST /api/detection/wheel-wobble/{ride_id}
Body: { "accelerometer_data": [...], "sample_rate": 50.0 }
Response: { "ride_id": 1, "wheel_wobble": { "detected": "fault", "confidence": 0.85, "detail": "..." } }
```

### 链条异响检测
```
POST /api/detection/chain-noise/{ride_id}
Body: { "audio_features": [...] }
```

### 车头不正检测
```
POST /api/detection/handlebar/{ride_id}
Body: { "gyroscope_data": [...], "sample_rate": 50.0 }
```

### 综合检测报告
```
GET /api/detection/report/{ride_id}
```
