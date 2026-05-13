from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SensorSample(BaseModel):
    """传感器单次采样数据 (加速度计或陀螺仪)"""

    x: float = Field(..., description="X轴分量 (加速度计: m/s², 陀螺仪: rad/s)", examples=[0.12])
    y: float = Field(..., description="Y轴分量 (加速度计: m/s², 陀螺仪: rad/s)", examples=[0.05])
    z: float = Field(..., description="Z轴分量 (加速度计静止≈9.81m/s², 陀螺仪偏航角 rad/s)", examples=[9.81])
    timestamp: float = Field(..., description="采集时间戳 (秒)", examples=[0.0])


class SensorBatch(BaseModel):
    """传感器批量数据（未启用，预留）"""

    ride_id: int = Field(..., description="骑行记录 ID", examples=[1])
    accelerometer: List[SensorSample] = Field(default_factory=list, description="加速度计数据列表")
    gyroscope: List[SensorSample] = Field(default_factory=list, description="陀螺仪数据列表")
    sample_rate: float = Field(default=50.0, description="采样率 (Hz)", examples=[50.0])


class AudioSegment(BaseModel):
    """音频片段（未启用，预留）"""

    ride_id: int = Field(..., description="骑行记录 ID", examples=[1])
    sample_rate: int = Field(default=44100, description="音频采样率 (Hz)", examples=[44100])
    duration: float = Field(..., description="音频时长 (秒)", examples=[5.0])
    features: List[float] = Field(default_factory=list, description="预提取的音频特征向量")


class WheelWobbleRequest(BaseModel):
    """轮胎偏摆检测请求 — 上传加速度计数据"""

    accelerometer_data: List[SensorSample] = Field(
        ...,
        description="加速度计采样序列。最少需要 sample_rate × 2 个样本（如 50Hz × 2 = 100 个样本 = 2 秒数据）。X轴=横向振动, Z轴=垂向振动（含重力）",
        json_schema_extra={
            "example": [
                {"x": 0.12, "y": 0.05, "z": 9.81, "timestamp": 0.0},
                {"x": 0.15, "y": 0.04, "z": 9.79, "timestamp": 0.02},
                {"x": 0.10, "y": 0.06, "z": 9.83, "timestamp": 0.04},
            ]
        },
    )
    sample_rate: float = Field(
        default=50.0,
        description="传感器采样率 (Hz)。用于校验数据时长：数据点数必须 >= sample_rate × 2。推荐值: 50Hz。",
        examples=[50.0],
    )


class HandlebarRequest(BaseModel):
    """车头不正检测请求 — 上传陀螺仪数据"""

    gyroscope_data: List[SensorSample] = Field(
        ...,
        description="陀螺仪采样序列。最少需要 sample_rate × 3 个样本（如 50Hz × 3 = 150 个样本 = 3 秒数据）。Z轴=偏航角速度，用于检测车头系统偏移。建议在直线骑行段采集。",
        json_schema_extra={
            "example": [
                {"x": 0.01, "y": 0.02, "z": 0.05, "timestamp": 0.0},
                {"x": 0.01, "y": 0.01, "z": 0.04, "timestamp": 0.02},
                {"x": 0.02, "y": 0.01, "z": 0.06, "timestamp": 0.04},
            ]
        },
    )
    sample_rate: float = Field(
        default=50.0,
        description="传感器采样率 (Hz)。用于校验数据时长：数据点数必须 >= sample_rate × 3。推荐值: 50Hz。",
        examples=[50.0],
    )


class ChainNoiseRequest(BaseModel):
    """链条异响检测请求 — 上传音频特征向量"""

    audio_features: List[float] = Field(
        ...,
        description="音频特征向量（预提取的 MFCC 均值等）。传入一组数值，算法计算均值与标准差进行异常检测。通常每段音频提取 13~20 维特征。",
        json_schema_extra={"example": [0.12, 0.08, 0.15, 0.11, 0.09, 0.13, 0.10]},
    )


class FaultDetectionResult(BaseModel):
    """故障检测综合报告（未启用，预留）"""

    ride_id: int = Field(..., description="骑行记录 ID")
    wheel_wobble: Optional[dict] = Field(None, description="轮胎偏摆检测结果 {detected, confidence, detail}")
    chain_noise: Optional[dict] = Field(None, description="链条异响检测结果 {detected, confidence, detail}")
    handlebar_misalignment: Optional[dict] = Field(None, description="车头不正检测结果 {detected, confidence, detail}")
    overall_status: str = Field(default="pending", description="综合状态: pending/completed")
