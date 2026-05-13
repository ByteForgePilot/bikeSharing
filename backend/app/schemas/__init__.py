from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SensorSample(BaseModel):
    x: float
    y: float
    z: float
    timestamp: float


class SensorBatch(BaseModel):
    ride_id: int
    accelerometer: List[SensorSample] = []
    gyroscope: List[SensorSample] = []
    sample_rate: float = Field(default=50.0, description="Hz")


class AudioSegment(BaseModel):
    ride_id: int
    sample_rate: int = 44100
    duration: float
    features: List[float] = []


class FaultDetectionResult(BaseModel):
    ride_id: int
    wheel_wobble: Optional[dict] = None
    chain_noise: Optional[dict] = None
    handlebar_misalignment: Optional[dict] = None
    overall_status: str = "pending"
