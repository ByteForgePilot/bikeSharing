from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user

router = APIRouter()


@router.post("/start")
async def start_ride(
    bike_id: str,
    lat: float = 0.0,
    lng: float = 0.0,
    user: dict = Depends(get_current_user),
):
    """Start a new ride session."""
    ride = {
        "id": 1,
        "user_id": user["id"],
        "bike_id": bike_id,
        "start_lat": lat,
        "start_lng": lng,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    return {"ride": ride, "message": "Ride started"}


@router.post("/{ride_id}/end")
async def end_ride(
    ride_id: int,
    lat: float = 0.0,
    lng: float = 0.0,
    user: dict = Depends(get_current_user),
):
    """End a ride and trigger fault analysis."""
    return {
        "ride_id": ride_id,
        "status": "completed",
        "message": "Ride ended, analysis queued",
    }


@router.post("/{ride_id}/sensor-data")
async def upload_sensor_data(
    ride_id: int,
    accelerometer: list,
    gyroscope: list,
    timestamps: list,
    user: dict = Depends(get_current_user),
):
    """Upload a batch of sensor readings for a ride."""
    return {
        "status": "received",
        "samples": len(timestamps),
        "ride_id": ride_id,
    }


@router.post("/{ride_id}/audio")
async def upload_audio_segment(
    ride_id: int,
    user: dict = Depends(get_current_user),
):
    """Upload an audio segment for chain noise analysis."""
    return {"status": "received", "ride_id": ride_id}


@router.get("/")
async def list_rides(
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    """List user's ride history."""
    return {"rides": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/{ride_id}")
async def get_ride(
    ride_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single ride with its fault analysis results."""
    return {"ride": None}
