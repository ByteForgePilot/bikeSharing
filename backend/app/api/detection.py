from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.services.sensor_analysis import analyze_wheel_wobble
from app.services.audio_analysis import analyze_chain_noise
from app.services.fault_classifier import classify_handlebar

router = APIRouter()


@router.post("/wheel-wobble/{ride_id}")
async def detect_wheel_wobble(
    ride_id: int,
    accelerometer_data: list,
    sample_rate: float = 50.0,
    user: dict = Depends(get_current_user),
):
    """Detect wheel wobble from accelerometer data."""
    result = analyze_wheel_wobble(accelerometer_data, sample_rate)
    return {"ride_id": ride_id, "wheel_wobble": result}


@router.post("/chain-noise/{ride_id}")
async def detect_chain_noise(
    ride_id: int,
    audio_features: list,
    user: dict = Depends(get_current_user),
):
    """Detect chain noise from audio features."""
    result = analyze_chain_noise(audio_features)
    return {"ride_id": ride_id, "chain_noise": result}


@router.post("/handlebar/{ride_id}")
async def detect_handlebar_misalignment(
    ride_id: int,
    gyroscope_data: list,
    sample_rate: float = 50.0,
    user: dict = Depends(get_current_user),
):
    """Detect handlebar misalignment from gyroscope yaw data."""
    result = classify_handlebar(gyroscope_data, sample_rate)
    return {"ride_id": ride_id, "handlebar_misalignment": result}


@router.get("/report/{ride_id}")
async def get_detection_report(
    ride_id: int,
    user: dict = Depends(get_current_user),
):
    """Get the combined fault detection report for a ride."""
    return {
        "ride_id": ride_id,
        "wheel_wobble": None,
        "chain_noise": None,
        "handlebar_misalignment": None,
        "overall_status": "pending",
    }
