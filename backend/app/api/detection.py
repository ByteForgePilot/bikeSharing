from fastapi import APIRouter, Depends, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas import (
    WheelWobbleRequest,
    HandlebarRequest,
    ChainNoiseRequest,
)
from app.services import detection as detection_service

router = APIRouter()

# Jinja2 templates (for dashboard)
templates = Jinja2Templates(directory="backend/app/templates")


# ---------------------------------------------------------------------------
# Individual detection endpoints (real-time, per-sensor)
# ---------------------------------------------------------------------------

@router.post(
    "/wheel-wobble/{ride_id}",
    summary="Tire wobble detection",
    description="Analyze accelerometer data using FFT + wheel-frequency analysis.",
)
async def detect_wheel_wobble(
    ride_id: int,
    body: WheelWobbleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = [d.model_dump() for d in body.accelerometer_data]
    result = await detection_service.detect_wheel_wobble(db, ride_id, data, body.sample_rate)
    return {"ride_id": ride_id, "wheel_wobble": result}


@router.post(
    "/chain-noise/{ride_id}",
    summary="Chain noise detection",
    description="Analyze audio features using envelope spectrum analysis.",
)
async def detect_chain_noise(
    ride_id: int,
    body: ChainNoiseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import numpy as np
    audio = np.array(body.audio_features, dtype=np.float32)
    result = await detection_service.detect_chain_noise(db, ride_id, audio)
    return {"ride_id": ride_id, "chain_noise": result}


@router.post(
    "/handlebar/{ride_id}",
    summary="Handlebar misalignment detection",
    description="Analyze gyroscope data for handlebar offset.",
)
async def detect_handlebar_misalignment(
    ride_id: int,
    body: HandlebarRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = [d.model_dump() for d in body.gyroscope_data]
    result = await detection_service.detect_handlebar(db, ride_id, data, body.sample_rate)
    return {"ride_id": ride_id, "handlebar_misalignment": result}


# ---------------------------------------------------------------------------
# File upload full detection (BicycleDataLogger output)
# ---------------------------------------------------------------------------

@router.post(
    "/upload/{ride_id}",
    summary="Upload BicycleDataLogger files for full detection",
    description="""Upload the three files produced by BicycleDataLogger:
- sensor: 传感器数据.txt (CSV with accel + gyro + GPS rows)
- audio_pcm: 音频.pcm (16-bit LE PCM)
- audio_ts: 音频_时间戳.csv (timestamp + cumulative samples)
Runs all three detections + composite health scoring.""",
)
async def upload_detection_files(
    ride_id: int,
    sensor: UploadFile = File(...),
    audio_pcm: UploadFile = File(...),
    audio_ts: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sensor_text = (await sensor.read()).decode("utf-8")
    pcm_bytes = await audio_pcm.read()
    ts_text = (await audio_ts.read()).decode("utf-8")

    result = await detection_service.detect_from_files(
        db, ride_id, sensor_text, pcm_bytes, ts_text
    )
    return result


# ---------------------------------------------------------------------------
# Web dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# API-compatible process endpoint (mirrors algorithm-branch Flask API)
@router.post("/process")
async def api_process(
    sensor: UploadFile = File(...),
    audio_pcm: UploadFile = File(...),
    audio_ts: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """File-upload detection without ride_id (standalone, no auth required)."""
    sensor_text = (await sensor.read()).decode("utf-8")
    pcm_bytes = await audio_pcm.read()
    ts_text = (await audio_ts.read()).decode("utf-8")

    from app.ml import (
        parse_sensor_csv,
        parse_pcm,
        parse_audio_ts,
        run_full_detection,
    )

    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts_list = parse_audio_ts(ts_text)

    result = run_full_detection(accel, gyro, audio, audio_ts_list)

    return {
        "health": result["health"],
        "f1_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f2_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f3_charts": _build_f3_charts(gyro),
        "data_summary": result["data_summary"],
    }


# ---------------------------------------------------------------------------
# Report query
# ---------------------------------------------------------------------------

@router.get(
    "/report/{ride_id}",
    summary="Get detection report",
    description="Get the comprehensive detection report for a ride.",
)
async def get_detection_report(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await detection_service.get_detection_report(db, ride_id)


@router.get(
    "/health-score/{ride_id}",
    summary="Get health score",
    description="Get the composite health score (0-100) for a ride.",
)
async def get_health_score(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await detection_service.get_detection_report(db, ride_id)
    return report


# ---------------------------------------------------------------------------
# Chart data helpers (for /api/process)
# ---------------------------------------------------------------------------

def _build_chart_data(accel, gyro, audio, audio_ts) -> dict:
    """Build minimal chart data; full charts computed on demand."""
    return {}


def _build_f3_charts(gyro) -> dict:
    return {}
