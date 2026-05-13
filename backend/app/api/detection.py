from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.services.sensor_analysis import analyze_wheel_wobble
from app.services.audio_analysis import analyze_chain_noise
from app.services.fault_classifier import classify_handlebar
from app.schemas import WheelWobbleRequest, HandlebarRequest, ChainNoiseRequest

router = APIRouter()


@router.post(
    "/wheel-wobble/{ride_id}",
    summary="轮胎偏摆检测",
    description="""
分析加速度计数据，检测轮胎偏摆故障。

**算法逻辑：**
计算 X/Z 轴的组合 RMS 振动能量，与阈值 (默认 0.3 m/s²) 对比。
- `normal`: 振动 < 阈值的一半 → 正常
- `suspect`: 振动在阈值一半到阈值之间 → 疑似故障
- `fault`: 振动 ≥ 阈值 → 确认故障
- `unknown`: 数据不足（需要 ≥ 2 秒数据）

**阈值参数**可通过 `wobble_threshold` 调整。
""",
    responses={
        200: {
            "description": "检测结果",
            "content": {
                "application/json": {
                    "example": {
                        "ride_id": 1,
                        "wheel_wobble": {
                            "detected": "suspect",
                            "confidence": 0.65,
                            "detail": "RMS vibration: 0.180 m/s² (threshold: 0.3)",
                        },
                    }
                }
            },
        },
        401: {"description": "未登录或 Token 过期"},
        422: {"description": "请求体格式不正确，请参考下方 Schema"},
    },
)
async def detect_wheel_wobble(
    ride_id: int,
    body: WheelWobbleRequest,
    user: dict = Depends(get_current_user),
):
    data = [d.model_dump() for d in body.accelerometer_data]
    result = analyze_wheel_wobble(data, body.sample_rate)
    return {"ride_id": ride_id, "wheel_wobble": result}


@router.post(
    "/chain-noise/{ride_id}",
    summary="链条异响检测",
    description="""
分析音频特征向量，检测链条异响故障。

**算法逻辑：**
计算特征向量的均值与标准差，构造异常分数与阈值对比。
- `normal`: 异常分数低 → 正常
- `suspect`: 异常分数中等 → 疑似故障
- `fault`: 异常分数高 → 确认故障
- `unknown`: 未传入特征数据

**注意：** 当前接收的是预计算的**特征向量**（非原始音频）。
特征值建议使用 MFCC 均值（13 维）或类似频谱特征。
""",
    responses={
        200: {
            "description": "检测结果",
            "content": {
                "application/json": {
                    "example": {
                        "ride_id": 1,
                        "chain_noise": {
                            "detected": "normal",
                            "confidence": 0.82,
                            "detail": "Anomaly score: 0.183 (mean=0.110, std=0.026)",
                        },
                    }
                }
            },
        },
        401: {"description": "未登录或 Token 过期"},
    },
)
async def detect_chain_noise(
    ride_id: int,
    body: ChainNoiseRequest,
    user: dict = Depends(get_current_user),
):
    result = analyze_chain_noise(body.audio_features)
    return {"ride_id": ride_id, "chain_noise": result}


@router.post(
    "/handlebar/{ride_id}",
    summary="车头不正检测",
    description="""
分析陀螺仪偏航角数据，检测车头不正故障。

**算法逻辑：**
1. 提取 Z 轴偏航角数据
2. 剔除 10% 离群值（消抖）
3. 计算均值偏移与阈值 (默认 3.0°) 对比

- `normal`: 偏移 < 阈值的一半 → 正常
- `suspect`: 偏移在阈值一半到阈值之间 → 疑似故障
- `fault`: 偏移 ≥ 阈值 → 确认故障
- `unknown`: 数据不足（需要 ≥ 3 秒数据）

**重要：** 此算法假设用户在**直线骑行**期间采集数据。
转弯时的偏航角偏移是正常的，应在数据采集前剔除弯道路段。
""",
    responses={
        200: {
            "description": "检测结果",
            "content": {
                "application/json": {
                    "example": {
                        "ride_id": 1,
                        "handlebar_misalignment": {
                            "detected": "fault",
                            "confidence": 0.75,
                            "detail": "Mean yaw offset: 5.20° (threshold: 3.0°)",
                        },
                    }
                }
            },
        },
        401: {"description": "未登录或 Token 过期"},
    },
)
async def detect_handlebar_misalignment(
    ride_id: int,
    body: HandlebarRequest,
    user: dict = Depends(get_current_user),
):
    data = [d.model_dump() for d in body.gyroscope_data]
    result = classify_handlebar(data, body.sample_rate)
    return {"ride_id": ride_id, "handlebar_misalignment": result}


@router.get(
    "/report/{ride_id}",
    summary="获取检测报告",
    description="获取指定骑行的综合故障检测报告（当前为 Stub，返回空结果）。",
    responses={401: {"description": "未登录或 Token 过期"}},
)
async def get_detection_report(
    ride_id: int,
    user: dict = Depends(get_current_user),
):
    return {
        "ride_id": ride_id,
        "wheel_wobble": None,
        "chain_noise": None,
        "handlebar_misalignment": None,
        "overall_status": "pending",
    }
