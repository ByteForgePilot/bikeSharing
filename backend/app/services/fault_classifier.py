"""Handlebar misalignment detection via gyroscope yaw analysis.

A misaligned handlebar creates a systematic offset: the bike travels straight
only when the handlebar is held at a non-zero angle relative to the frame.

Detection strategy:
1. Collect gyroscope yaw (rotation around vertical axis) during straight-line riding
2. Compute mean yaw offset — a healthy bike should average near 0
3. Compare absolute mean offset to threshold
"""

from typing import List


def classify_handlebar(
    gyroscope_data: List[dict],
    sample_rate: float = 50.0,
    offset_threshold_deg: float = 3.0,
) -> dict:
    """Analyze gyroscope data for handlebar misalignment.

    Args:
        gyroscope_data: List of {x, y, z, timestamp} dicts (z = yaw axis).
        sample_rate: Sensor sample rate in Hz.
        offset_threshold_deg: Yaw offset threshold in degrees.

    Returns:
        dict with keys: detected, confidence, detail.
    """
    if len(gyroscope_data) < sample_rate * 3:
        return {
            "detected": "unknown",
            "confidence": 0.0,
            "detail": "Insufficient data (need >= 3 seconds)",
        }

    import math

    # Extract yaw (z-axis rotation)
    yaw_vals = [d["z"] for d in gyroscope_data]

    # Remove outliers: trim top/bottom 10%
    sorted_yaw = sorted(yaw_vals)
    trim = len(sorted_yaw) // 10
    trimmed = sorted_yaw[trim : -trim] if trim > 0 else sorted_yaw

    mean_yaw = sum(trimmed) / len(trimmed)

    # Compute confidence based on how far the offset exceeds threshold
    abs_offset = abs(mean_yaw)
    ratio = abs_offset / offset_threshold_deg

    if ratio < 0.5:
        status = "normal"
        confidence = 1.0 - ratio
    elif ratio < 1.0:
        status = "suspect"
        confidence = ratio
    else:
        status = "fault"
        confidence = min(ratio / 2, 1.0)

    confidence = round(max(0.0, min(confidence, 1.0)), 2)

    return {
        "detected": status,
        "confidence": confidence,
        "detail": f"Mean yaw offset: {mean_yaw:.2f}° (threshold: {offset_threshold_deg}°)",
    }
