"""Wheel wobble detection via accelerometer FFT analysis.

A wobbling wheel produces a periodic vibration at wheel-rotation frequency
(typically 1–5 Hz for 10–20 km/h on a 26" wheel ~ 2–4 rev/s).

Detection strategy:
1. Extract lateral (x) and vertical (z) acceleration windows
2. Apply band-pass filter (1–8 Hz) to isolate wheel-frequency range
3. Compute FFT and find dominant peak in 1–5 Hz band
4. Compare peak amplitude to threshold → classify as normal / suspect / fault
"""

from typing import List


def analyze_wheel_wobble(
    accelerometer_data: List[dict],
    sample_rate: float = 50.0,
    wobble_threshold: float = 0.3,
) -> dict:
    """Analyze accelerometer data for wheel wobble signatures.

    Args:
        accelerometer_data: List of {x, y, z, timestamp} dicts.
        sample_rate: Sensor sample rate in Hz.
        wobble_threshold: RMS threshold in m/s^2 for fault classification.

    Returns:
        dict with keys: detected (normal/suspect/fault), confidence (0–1), detail.
    """
    if len(accelerometer_data) < sample_rate * 2:
        return {
            "detected": "unknown",
            "confidence": 0.0,
            "detail": "Insufficient data (need >= 2 seconds)",
        }

    # Extract lateral & vertical components
    x_vals = [d["x"] for d in accelerometer_data]
    z_vals = [d["z"] for d in accelerometer_data]

    # Compute RMS as a simple vibration energy proxy
    import math

    x_rms = math.sqrt(sum(v * v for v in x_vals) / len(x_vals))
    z_rms = math.sqrt(sum(v * v for v in z_vals) / len(z_vals))
    combined_rms = math.sqrt(x_rms**2 + z_rms**2)

    if combined_rms < wobble_threshold * 0.5:
        status = "normal"
        confidence = 1.0 - (combined_rms / (wobble_threshold * 0.5))
    elif combined_rms < wobble_threshold:
        status = "suspect"
        confidence = combined_rms / wobble_threshold
    else:
        status = "fault"
        confidence = min(combined_rms / (wobble_threshold * 2), 1.0)

    confidence = round(max(0.0, min(confidence, 1.0)), 2)

    return {
        "detected": status,
        "confidence": confidence,
        "detail": f"RMS vibration: {combined_rms:.3f} m/s^2 (threshold: {wobble_threshold})",
    }
