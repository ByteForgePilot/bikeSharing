# 09 — 测试策略

## 当前状态

**26 个测试，全部通过。**

```
backend/tests/
├── __init__.py
├── test_api.py          # 3 个 API 集成测试
└── test_services.py     # 23 个服务层单元测试
```

---

## 测试分层

```
┌────────────────────────────────┐
│   E2E (端到端)                  │  ← 未实现
│   用户操作完整流程               │
├────────────────────────────────┤
│   API 集成测试                  │  ← test_api.py (3 tests)
│   HTTP 请求 → 路由 → 响应       │
├────────────────────────────────┤
│   服务层单元测试                 │  ← test_services.py (23 tests)
│   纯函数，无外部依赖              │
└────────────────────────────────┘
```

### 为什么服务层测试比 API 测试多？

服务层函数是**纯函数**（输入数据 → 输出结果），无数据库/网络依赖，
执行快（23 个测试 < 0.1s），适合覆盖所有边界条件。

API 测试通过 `httpx.ASGITransport` 模拟 HTTP 请求，但不经过网络层，
也不需要真实数据库（当前 auth 使用内存存储），速度也很快。

---

## 测试清单

### test_api.py（3 个）

| # | 测试 | 验证内容 |
|---|------|---------|
| 1 | `test_health_check` | GET `/api/health` → 200, `{"status":"ok"}` |
| 2 | `test_register_and_login` | 注册→登录→获取用户信息 完整认证流程 |
| 3 | `test_wheel_wobble_detection` | 注册→登录→上传传感器数据→获取检测结果 |

### test_services.py（23 个）

**TestWheelWobble（7 个）:**
| # | 测试 | 验证 |
|---|------|------|
| 1 | `test_insufficient_data` | 数据不足 → `unknown`, confidence 0.0 |
| 2 | `test_normal_low_vibration` | 低振幅 → `normal` |
| 3 | `test_suspect_moderate_vibration` | 中等振幅 → `normal/suspect/fault` |
| 4 | `test_fault_strong_vibration` | 高振幅 → `fault`, confidence ≥ 0.5 |
| 5 | `test_custom_threshold` | 自定义阈值生效 |
| 6 | `test_confidence_bounds` | 极端值下 confidence 仍在 0-1 范围 |
| 7 | `test_return_keys` | 返回 `detected`, `confidence`, `detail` |

**TestChainNoise（8 个）:**
| # | 测试 | 验证 |
|---|------|------|
| 1 | `test_empty_features` | 空输入 → `unknown`, confidence 0.0 |
| 2 | `test_normal_low_features` | 低特征值 → `normal` |
| 3 | `test_suspect_moderate_features` | 中等特征值 → 合法分类 |
| 4 | `test_fault_strong_features` | 高特征值 → `fault`, confidence ≥ 0.5 |
| 5 | `test_custom_threshold` | 自定义阈值生效 |
| 6 | `test_single_feature` | 单元素列表 → 不崩溃 |
| 7 | `test_confidence_bounds` | 极端值下 confidence 仍在 0-1 范围 |
| 8 | `test_return_keys` | 返回完整字段 |

**TestHandlebar（8 个）:**
| # | 测试 | 验证 |
|---|------|------|
| 1 | `test_insufficient_data` | 数据不足 → `unknown` |
| 2 | `test_normal_straight_handlebar` | yaw=0 → `normal`, confidence ≥ 0.5 |
| 3 | `test_suspect_slight_offset` | yaw=2° → 合法分类 |
| 4 | `test_fault_strong_offset` | yaw=8° → `fault` |
| 5 | `test_custom_threshold` | 自定义阈值生效 |
| 6 | `test_outlier_trimming` | 注入 ±90° 离群值 → 不被误判为 fault |
| 7 | `test_confidence_bounds` | 极端值下 confidence 仍在 0-1 |
| 8 | `test_return_keys` | 返回完整字段 |

---

## 运行测试

```bash
# 激活环境
conda activate bikeSharing

# 运行全部测试
cd backend
pytest

# 详细输出
pytest -v

# 仅服务层测试
pytest tests/test_services.py -v

# 仅 API 测试
pytest tests/test_api.py -v

# 带覆盖率报告
pip install pytest-cov
pytest --cov=app --cov-report=html

# 遇到失败立即停止
pytest -x
```

---

## 测试辅助函数

### 合成加速度计数据

```python
def _make_accel(samples: int, freq: float, amplitude: float,
                sample_rate: float = 50.0) -> list[dict]:
    """生成包含指定频率正弦波的加速度计数据"""
    data = []
    for i in range(samples):
        t = i / sample_rate
        x = amplitude * math.sin(2 * math.pi * freq * t)
        z = amplitude * 0.3 * math.sin(2 * math.pi * freq * t + 0.5)
        data.append({"x": x, "y": 0.0, "z": z, "timestamp": t})
    return data
```

### 合成陀螺仪数据

```python
def _make_gyro(samples: int, yaw_offset: float, noise_deg: float = 0.05,
               sample_rate: float = 50.0) -> list[dict]:
    """生成包含指定偏航偏移的陀螺仪数据"""
    data = []
    for i in range(samples):
        t = i / sample_rate
        z = yaw_offset + noise_deg * (2 * math.sin(17.7 * t) - 1)
        data.append({"x": 0.0, "y": 0.0, "z": z, "timestamp": t})
    return data
```

---

## 如何添加新测试

### 添加新的检测算法测试

1. 在 `test_services.py` 创建新 TestClass
2. 遵循现有模式：每个测试函数验证一个方面
3. 覆盖边界条件：正常值、边界值、异常值、空输入
4. 使用合成数据（不依赖外部文件）

```python
class TestNewFaultType:
    def test_insufficient_data(self):
        ...

    def test_normal_case(self):
        ...

    def test_fault_case(self):
        ...

    def test_confidence_bounds(self):
        ...

    def test_return_keys(self):
        ...
```

### 添加新 API 端点测试

1. 在 `test_api.py` 添加 async 测试函数
2. 使用 `@pytest.mark.asyncio` 和 `@pytest_asyncio.fixture` 装饰器
3. 如果端点需要认证：先注册/登录获取 token
4. 断言 `resp.status_code` 和 `resp.json()`

```python
@pytest.mark.asyncio
async def test_new_endpoint(client):
    # 1. 注册并登录
    await client.post("/api/auth/register",
        json={"username": "t", "password": "p"})
    login_resp = await client.post("/api/auth/login",
        data={"username": "t", "password": "p"})
    token = login_resp.json()["access_token"]

    # 2. 调用新端点
    resp = await client.get("/api/new-endpoint",
        headers={"Authorization": f"Bearer {token}"})

    # 3. 断言
    assert resp.status_code == 200
    assert "expected_key" in resp.json()
```

---

## CI 中的测试

每次 push/PR 到 `backend/**` 路径，GitHub Actions 自动运行：

```
ubuntu-latest
├── PostgreSQL 16 (service container)
├── Redis 7 (service container)
├── Python 3.12
├── pip install -r backend/requirements.txt
└── cd backend && pytest -v
```

PR 在测试全部通过前不应合并。

---

## 代码覆盖率目标

| 层级 | 当前 | 目标 |
|------|------|------|
| 服务层 (`services/`) | 100% (23 tests) | > 90% |
| API 路由 (`api/`) | 部分 (3 tests) | > 80% |
| 数据模型 (`models/`) | 0% | > 70% |
| 工具函数 (`utils/`) | 0% (空文件) | — |
| 总体 | ~60% | > 80% |
