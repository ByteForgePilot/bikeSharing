from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.ride import Ride
from app.api.auth import get_current_user

router = APIRouter()


class SensorDataUpload(BaseModel):
    accelerometer: list = Field(default_factory=list, description="加速度计数据 [{x, y, z, timestamp}]")
    gyroscope: list = Field(default_factory=list, description="陀螺仪数据 [{x, y, z, timestamp}]")


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


@router.post(
    "/start",
    summary="开始骑行",
    description="创建新的骑行会话。用户需先登录。",
    responses={401: {"description": "未登录或 Token 过期"}},
)
async def start_ride(
    bike_id: str,
    lat: float = 0.0,
    lng: float = 0.0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = Ride(
        user_id=user.id,
        bike_id=bike_id,
        start_lat=lat,
        start_lng=lng,
    )
    db.add(ride)
    await db.commit()
    await db.refresh(ride)
    return {
        "ride": {
            "id": ride.id,
            "user_id": ride.user_id,
            "bike_id": ride.bike_id,
            "start_lat": ride.start_lat,
            "start_lng": ride.start_lng,
            "started_at": ride.started_at.isoformat() if ride.started_at else None,
            "status": ride.status,
        },
        "message": "Ride started",
    }


@router.post(
    "/{ride_id}/end",
    summary="结束骑行",
    description="结束指定骑行并触发故障分析。",
    responses={
        401: {"description": "未登录或 Token 过期"},
        404: {"description": "骑行记录不存在"},
    },
)
async def end_ride(
    ride_id: int,
    lat: float = 0.0,
    lng: float = 0.0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = await db.get(Ride, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    ride.end_lat = lat
    ride.end_lng = lng
    ride.ended_at = datetime.now(timezone.utc)
    ride.status = "completed"
    await db.commit()
    return {
        "ride_id": ride_id,
        "status": "completed",
        "message": "Ride ended, analysis queued",
    }


@router.post(
    "/{ride_id}/sensor-data",
    summary="上传传感器数据",
    description="为指定骑行上传一批加速度计和陀螺仪读数。",
    responses={
        401: {"description": "未登录或 Token 过期"},
        404: {"description": "骑行记录不存在或不属于当前用户"},
    },
)
async def upload_sensor_data(
    ride_id: int,
    body: SensorDataUpload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = await db.get(Ride, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    return {
        "status": "received",
        "samples": max(len(body.accelerometer), len(body.gyroscope)),
        "ride_id": ride_id,
    }


@router.post(
    "/{ride_id}/audio",
    summary="上传音频数据",
    description="为指定骑行上传音频片段用于链条异响分析。",
    responses={
        401: {"description": "未登录或 Token 过期"},
        404: {"description": "骑行记录不存在或不属于当前用户"},
    },
)
async def upload_audio_segment(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = await db.get(Ride, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    return {"status": "received", "ride_id": ride_id}


@router.get(
    "/",
    summary="骑行历史列表",
    description="获取当前用户的骑行历史记录，支持分页。",
)
async def list_rides(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_q = select(func.count()).select_from(Ride).where(Ride.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Ride)
        .where(Ride.user_id == user.id)
        .order_by(Ride.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    rides = result.scalars().all()
    return {
        "rides": [
            {
                "id": r.id,
                "bike_id": r.bike_id,
                "start_lat": r.start_lat,
                "start_lng": r.start_lng,
                "end_lat": r.end_lat,
                "end_lng": r.end_lng,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "status": r.status,
            }
            for r in rides
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{ride_id}",
    summary="获取骑行详情",
    description="获取指定骑行的详细信息及故障检测结果。",
    responses={
        401: {"description": "未登录或 Token 过期"},
        404: {"description": "骑行记录不存在"},
    },
)
async def get_ride(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = await db.get(Ride, ride_id)
    if not ride or ride.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    return {
        "ride": {
            "id": ride.id,
            "user_id": ride.user_id,
            "bike_id": ride.bike_id,
            "start_lat": ride.start_lat,
            "start_lng": ride.start_lng,
            "end_lat": ride.end_lat,
            "end_lng": ride.end_lng,
            "started_at": ride.started_at.isoformat() if ride.started_at else None,
            "ended_at": ride.ended_at.isoformat() if ride.ended_at else None,
            "status": ride.status,
        }
    }
