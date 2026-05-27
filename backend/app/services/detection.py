from app.repositories import fault_report as report_repo
from app.services.sensor_analysis import analyze_wheel_wobble
from app.services.audio_analysis import analyze_chain_noise
from app.services.fault_classifier import classify_handlebar


async def detect_wheel_wobble(db, ride_id: int, data: list[dict], sample_rate: float) -> dict:
    result = analyze_wheel_wobble(data, sample_rate)
    await report_repo.upsert(
        db,
        ride_id,
        {
            "wheel_wobble_detected": result["detected"],
            "wheel_wobble_confidence": result["confidence"],
            "wheel_wobble_detail": result["detail"],
        },
    )
    return result


async def detect_chain_noise(db, ride_id: int, features: list[float]) -> dict:
    result = analyze_chain_noise(features)
    await report_repo.upsert(
        db,
        ride_id,
        {
            "chain_noise_detected": result["detected"],
            "chain_noise_confidence": result["confidence"],
            "chain_noise_detail": result["detail"],
        },
    )
    return result


async def detect_handlebar(db, ride_id: int, data: list[dict], sample_rate: float) -> dict:
    result = classify_handlebar(data, sample_rate)
    await report_repo.upsert(
        db,
        ride_id,
        {
            "handlebar_detected": result["detected"],
            "handlebar_confidence": result["confidence"],
            "handlebar_detail": result["detail"],
        },
    )
    return result


async def get_detection_report(db, ride_id: int) -> dict:
    report = await report_repo.get_by_ride_id(db, ride_id)
    if report is None:
        return {
            "ride_id": ride_id,
            "wheel_wobble": None,
            "chain_noise": None,
            "handlebar_misalignment": None,
            "overall_status": "pending",
        }

    def _build(field: str) -> dict | None:
        detected = getattr(report, f"{field}_detected", "unknown")
        if detected == "unknown" and getattr(report, f"{field}_confidence") is None:
            return None
        return {
            "detected": detected,
            "confidence": getattr(report, f"{field}_confidence"),
            "detail": getattr(report, f"{field}_detail"),
        }

    wheel = _build("wheel_wobble")
    chain = _build("chain_noise")
    handlebar = _build("handlebar")

    results = [r for r in (wheel, chain, handlebar) if r is not None]
    if not results:
        overall = "pending"
    elif all(r["detected"] == "normal" for r in results):
        overall = "normal"
    elif any(r["detected"] == "fault" for r in results):
        overall = "fault"
    else:
        overall = "suspect"

    return {
        "ride_id": ride_id,
        "wheel_wobble": wheel,
        "chain_noise": chain,
        "handlebar_misalignment": handlebar,
        "overall_status": overall,
    }
