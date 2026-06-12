from typing import List, Optional

from pydantic import BaseModel, Field


class SensorSample(BaseModel):
    x: float = Field(..., description="X axis (accel: m/s^2, gyro: rad/s)", examples=[0.12])
    y: float = Field(..., description="Y axis", examples=[0.05])
    z: float = Field(..., description="Z axis (accel gravity ~9.81 m/s^2, gyro yaw rad/s)", examples=[9.81])
    timestamp: float = Field(..., description="Collection timestamp (seconds)", examples=[0.0])


class WheelWobbleRequest(BaseModel):
    accelerometer_data: List[SensorSample] = Field(..., description="Accelerometer samples. Minimum sample_rate * 2 samples.")
    sample_rate: float = Field(default=100.0, description="Sensor sample rate (Hz)", examples=[100.0])


class HandlebarRequest(BaseModel):
    gyroscope_data: List[SensorSample] = Field(..., description="Gyroscope samples. Minimum sample_rate * 3 samples.")
    sample_rate: float = Field(default=50.0, description="Sensor sample rate (Hz)", examples=[50.0])


class ChainNoiseRequest(BaseModel):
    audio_features: List[float] = Field(..., description="Audio feature vector (MFCC means, etc.)", examples=[[0.12, 0.08, 0.15]])


class DetectionResult(BaseModel):
    detected: str = Field(..., description="normal / suspect / fault / unknown")
    confidence: float = Field(..., description="Confidence 0-1")
    detail: str = Field(..., description="Human-readable detail")
    score: Optional[float] = Field(default=None, description="0-100 score")


class HealthScoreResponse(BaseModel):
    ride_id: int
    total_score: Optional[float] = None
    recommendation: Optional[str] = None
    tire_score: Optional[float] = None
    chain_score: Optional[float] = None
    handlebar_score: Optional[float] = None
    overall_status: str = "pending"
    details: Optional[dict] = None
