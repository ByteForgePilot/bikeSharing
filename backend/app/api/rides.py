from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories import fault_report as report_repo
from app.schemas.ride import SensorDataUpload
from app.services import ride as ride_service
from app.services.audio_analysis import analyze_chain_noise, decode_audio_to_samples

router = APIRouter()


@router.post(
    "/start",
    summary="开始骑行",
    description="创建新的骑行会话。用户需先登录。",
    responses={401: {"description": "未登录或 Token 过期"}},
)
async def start_ride(
    bike_id: str = Query(...),
    lat: float = Query(0.0),
    lng: float = Query(0.0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = await ride_service.start_ride(db, user, bike_id, lat, lng)
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
    lat: float = Query(0.0),
    lng: float = Query(0.0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ride = await ride_service.end_ride(db, user, ride_id, lat, lng)
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
    await ride_service.verify_ride_ownership(db, user, ride_id)
    return {
        "status": "received",
        "samples": max(len(body.accelerometer), len(body.gyroscope)),
        "ride_id": ride_id,
    }


@router.post(
    "/{ride_id}/audio",
    summary="上传音频数据",
    description="上传 WAV 音频文件用于链条异响分析。",
    responses={
        401: {"description": "未登录或 Token 过期"},
        404: {"description": "骑行记录不存在或不属于当前用户"},
    },
)
async def upload_audio_segment(
    ride_id: int,
    audio_file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ride_service.verify_ride_ownership(db, user, ride_id)

    audio_bytes = await audio_file.read()
    samples = decode_audio_to_samples(audio_bytes)
    result = analyze_chain_noise(samples.tolist())

    await report_repo.upsert(
        db, ride_id,
        {
            "chain_noise_detected": result["detected"],
            "chain_noise_confidence": result["confidence"],
            "chain_noise_detail": result["detail"],
        },
    )

    return {"ride_id": ride_id, "chain_noise": result}


@router.get(
    "/",
    summary="骑行历史列表",
    description="获取当前用户的骑行历史记录，支持分页。",
)
async def list_rides(
    limit: int = Query(20),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ride_service.list_user_rides(db, user, limit, offset)


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
    ride = await ride_service.get_ride_detail(db, user, ride_id)
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
