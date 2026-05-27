from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas import WheelWobbleRequest, HandlebarRequest, ChainNoiseRequest
from app.services import detection as detection_service

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
        422: {"description": "请求体格式不正确"},
    },
)
async def detect_wheel_wobble(
    ride_id: int,
    body: WheelWobbleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = [d.model_dump() for d in body.accelerometer_data]
    result = await detection_service.detect_wheel_wobble(db, ride_id, data, body.sample_rate)
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await detection_service.detect_chain_noise(db, ride_id, body.audio_features)
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = [d.model_dump() for d in body.gyroscope_data]
    result = await detection_service.detect_handlebar(db, ride_id, data, body.sample_rate)
    return {"ride_id": ride_id, "handlebar_misalignment": result}


@router.get(
    "/report/{ride_id}",
    summary="获取检测报告",
    description="获取指定骑行的综合故障检测报告。",
    responses={401: {"description": "未登录或 Token 过期"}},
)
async def get_detection_report(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await detection_service.get_detection_report(db, ride_id)
