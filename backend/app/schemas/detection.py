from typing import List

from pydantic import BaseModel, Field


class SensorSample(BaseModel):
    x: float = Field(..., description="X轴分量 (加速度计: m/s², 陀螺仪: rad/s)", examples=[0.12])
    y: float = Field(..., description="Y轴分量 (加速度计: m/s², 陀螺仪: rad/s)", examples=[0.05])
    z: float = Field(..., description="Z轴分量 (加速度计静止≈9.81m/s², 陀螺仪偏航角 rad/s)", examples=[9.81])
    timestamp: float = Field(..., description="采集时间戳 (秒)", examples=[0.0])


class WheelWobbleRequest(BaseModel):
    accelerometer_data: List[SensorSample] = Field(
        ...,
        description="加速度计采样序列。最少需要 sample_rate × 2 个样本。",
        json_schema_extra={
            "example": [
                {"x": 0.12, "y": 0.05, "z": 9.81, "timestamp": 0.0},
                {"x": 0.15, "y": 0.04, "z": 9.79, "timestamp": 0.02},
                {"x": 0.10, "y": 0.06, "z": 9.83, "timestamp": 0.04},
            ]
        },
    )
    sample_rate: float = Field(default=50.0, description="传感器采样率 (Hz)", examples=[50.0])


class HandlebarRequest(BaseModel):
    gyroscope_data: List[SensorSample] = Field(
        ...,
        description="陀螺仪采样序列。最少需要 sample_rate × 3 个样本。Z轴=偏航角速度。",
        json_schema_extra={
            "example": [
                {"x": 0.01, "y": 0.02, "z": 0.05, "timestamp": 0.0},
                {"x": 0.01, "y": 0.01, "z": 0.04, "timestamp": 0.02},
                {"x": 0.02, "y": 0.01, "z": 0.06, "timestamp": 0.04},
            ]
        },
    )
    sample_rate: float = Field(default=50.0, description="传感器采样率 (Hz)", examples=[50.0])


class ChainNoiseRequest(BaseModel):
    audio_features: List[float] = Field(
        ...,
        description="音频特征向量（预提取的 MFCC 均值等）",
        json_schema_extra={"example": [0.12, 0.08, 0.15, 0.11, 0.09, 0.13, 0.10]},
    )


class FaultDetectionResult(BaseModel):
    ride_id: int = Field(..., description="骑行记录 ID")
    wheel_wobble: dict | None = Field(None, description="轮胎偏摆检测结果 {detected, confidence, detail}")
    chain_noise: dict | None = Field(None, description="链条异响检测结果 {detected, confidence, detail}")
    handlebar_misalignment: dict | None = Field(None, description="车头不正检测结果 {detected, confidence, detail}")
    overall_status: str = Field(default="pending", description="综合状态: pending/completed")
