from pydantic import BaseModel, Field


class SensorDataUpload(BaseModel):
    accelerometer: list = Field(default_factory=list, description="加速度计数据 [{x, y, z, timestamp}]")
    gyroscope: list = Field(default_factory=list, description="陀螺仪数据 [{x, y, z, timestamp}]")
    gps: list = Field(default_factory=list, description="GPS 数据 [{lat, lng, altitude, accuracy, timestamp}]")


class RideResponse(BaseModel):
    id: int
    user_id: int
    bike_id: str
    start_lat: float
    start_lng: float
    end_lat: float | None = None
    end_lng: float | None = None
    started_at: str
    ended_at: str | None = None
    status: str

    model_config = {"from_attributes": True}


class RideListResponse(BaseModel):
    rides: list[dict]
    total: int
    limit: int
    offset: int
