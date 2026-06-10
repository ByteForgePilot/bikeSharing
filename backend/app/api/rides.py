from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.ride import SensorDataUpload
from app.services import ride as ride_service
from app.services import detection as detection_service
from app.services.detection_engine import parse_audio_bytes

router = APIRouter()


@router.post(
    "/start",
    summary="Start ride",
    description="Create a new ride session. Requires login.",
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
    summary="End ride",
    description="End the specified ride.",
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
    summary="Upload sensor data",
    description="Upload a batch of accelerometer and gyroscope readings for a ride.",
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
    summary="Upload audio for chain noise detection",
    description="Upload WAV/PCM audio file for chain noise analysis using v3.0 envelope spectrum algorithm.",
)
async def upload_audio_segment(
    ride_id: int,
    audio_file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ride_service.verify_ride_ownership(db, user, ride_id)

    audio_bytes = await audio_file.read()
    audio = parse_audio_bytes(audio_bytes)
    result = await detection_service.detect_chain_noise(db, ride_id, audio)

    return {"ride_id": ride_id, "chain_noise": result}


@router.get(
    "/",
    summary="Ride history",
    description="Get current user ride history with pagination.",
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
    summary="Get ride details",
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
