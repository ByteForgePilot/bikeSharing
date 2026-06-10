"""Detection orchestration service --- calls the v3.0 algorithm engine."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import fault_report as report_repo
from app.services.detection_engine import (
    dicts_to_accel,
    dicts_to_gyro,
    run_f1_tire_wobble,
    run_f2_chain_noise,
    run_f3_handlebar,
    run_full_detection,
    parse_sensor_csv,
    parse_pcm,
    parse_audio_ts,
    parse_audio_bytes,
)


# ---------------------------------------------------------------------------
# Individual detection functions (called by API endpoints)
# ---------------------------------------------------------------------------

async def detect_wheel_wobble(
    db: AsyncSession, ride_id: int, data: list[dict], sample_rate: float
) -> dict:
    accel = dicts_to_accel(data)
    result = run_f1_tire_wobble(accel)

    await report_repo.upsert(
        db,
        ride_id,
        {
            "tire_score": result["score"],
            "wheel_wobble_detail": json.dumps(result, ensure_ascii=False),
        },
    )
    return _to_api_format(result, "tire")


async def detect_chain_noise(
    db: AsyncSession, ride_id: int, audio: "np.ndarray",
    audio_chunks: list | None = None,
    pedal_freq_hz: float | None = None,
) -> dict:
    result = run_f2_chain_noise(audio, audio_chunks or [], pedal_freq_hz)

    await report_repo.upsert(
        db,
        ride_id,
        {
            "chain_score": result["score"],
            "chain_noise_detail": json.dumps(result, ensure_ascii=False),
        },
    )
    return _to_api_format(result, "chain")


async def detect_handlebar(
    db: AsyncSession, ride_id: int, data: list[dict], sample_rate: float
) -> dict:
    gyro = dicts_to_gyro(data)
    result = run_f3_handlebar(gyro)

    await report_repo.upsert(
        db,
        ride_id,
        {
            "handlebar_score": result["score"],
            "handlebar_detail": json.dumps(result, ensure_ascii=False),
        },
    )
    return _to_api_format(result, "handlebar")


# ---------------------------------------------------------------------------
# File-upload full detection
# ---------------------------------------------------------------------------

async def detect_from_files(
    db: AsyncSession,
    ride_id: int,
    sensor_text: str,
    pcm_bytes: bytes,
    ts_text: str,
) -> dict:
    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts = parse_audio_ts(ts_text)

    result = run_full_detection(accel, gyro, audio, audio_ts)
    health = result["health"]

    await report_repo.upsert(
        db,
        ride_id,
        {
            "tire_score": health["sub_scores"]["tire_wobble"],
            "chain_score": health["sub_scores"]["chain_noise"],
            "handlebar_score": health["sub_scores"]["handlebar_misalignment"],
            "total_score": health["total_score"],
            "recommendation": health["recommendation"],
            "details_json": json.dumps(health["details"], ensure_ascii=False),
            "wheel_wobble_detail": json.dumps(result["f1"], ensure_ascii=False),
            "chain_noise_detail": json.dumps(result["f2"], ensure_ascii=False),
            "handlebar_detail": json.dumps(result["f3"], ensure_ascii=False),
        },
    )

    return {
        "ride_id": ride_id,
        "health": health,
        "f1": result["f1"],
        "f2": result["f2"],
        "f3": result["f3"],
        "data_summary": result["data_summary"],
        "window_used": result["window_used"],
    }


# ---------------------------------------------------------------------------
# Report query
# ---------------------------------------------------------------------------

async def get_detection_report(db: AsyncSession, ride_id: int) -> dict:
    report = await report_repo.get_by_ride_id(db, ride_id)
    if report is None:
        return {
            "ride_id": ride_id,
            "total_score": None,
            "recommendation": None,
            "tire_score": None,
            "chain_score": None,
            "handlebar_score": None,
            "overall_status": "pending",
        }

    scores = [
        s
        for s in (report.tire_score, report.chain_score, report.handlebar_score)
        if s is not None
    ]
    if not scores:
        overall = "pending"
    elif report.total_score is not None and report.total_score >= 70:
        overall = "good"
    elif report.total_score is not None and report.total_score >= 50:
        overall = "caution"
    elif report.total_score is not None:
        overall = "bad"
    else:
        overall = "pending"

    return {
        "ride_id": ride_id,
        "total_score": report.total_score,
        "recommendation": report.recommendation,
        "tire_score": report.tire_score,
        "chain_score": report.chain_score,
        "handlebar_score": report.handlebar_score,
        "overall_status": overall,
        "details": json.loads(report.details_json) if report.details_json else None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_api_format(algo_result: dict, fault_type: str) -> dict:
    """Convert algorithm output to the API''s {detected, confidence, detail} format."""
    score = algo_result.get("score", 100.0)
    if score >= 80:
        detected, confidence = "normal", score / 100.0
    elif score >= 40:
        detected, confidence = "suspect", 0.5 + (80 - score) / 80
    else:
        detected, confidence = "fault", (100 - score) / 100.0

    # Build a human-readable detail string
    if fault_type == "tire":
        detail = (
            f"P={algo_result.get('P_value', 0):.4f} "
            f"wheel_freq={algo_result.get('wheel_freq_hz', 0):.1f}Hz "
            f"flat={algo_result.get('flat_fraction', 0):.0%}"
        )
    elif fault_type == "chain":
        detail = (
            f"{algo_result.get('prediction', '未知')} "
            f"conf={algo_result.get('confidence', 0):.3f} "
            f"SNR={algo_result.get('pedal_snr_db', 0):.1f}dB"
        )
    else:
        detail = (
            f"Δθ={algo_result.get('delta_theta_deg', 0):.2f}° "
            f"bias={algo_result.get('yaw_bias_rad_s', 0):.4f}rad/s"
        )

    return {
        "detected": detected,
        "confidence": round(confidence, 2),
        "detail": detail,
        "score": round(score, 2),
    }


