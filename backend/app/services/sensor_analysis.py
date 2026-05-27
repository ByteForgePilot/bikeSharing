"""Wheel wobble detection via STFT time-frequency analysis.

A wobbling wheel produces sustained periodic vibration at wheel-rotation
frequency (1–5 Hz for 10–20 km/h on a 26" wheel). Transient road noise
(bumps, gravel) spreads across higher frequencies and is intermittent.

Detection strategy:
1. Combine lateral (x) + vertical (z) into a single vibration signal
2. Compute STFT to get frequency energy over time windows
3. Extract energy in 1–5 Hz band vs total energy per window
4. Measure "persistence" — how many windows show elevated 1–5 Hz energy
5. Classify based on both energy ratio and persistence
"""

import math
from typing import List


def _rms(vals: List[float]) -> float:
    return math.sqrt(sum(v * v for v in vals) / len(vals)) if vals else 0.0


def analyze_wheel_wobble(
    accelerometer_data: List[dict],
    sample_rate: float = 20.0,
    wobble_threshold: float = 0.3,
) -> dict:
    """Analyze accelerometer data for wheel wobble using STFT.

    Uses scipy.signal.stft when available, falling back to a simpler
    FFT-based approach if scipy is not installed.

    Args:
        accelerometer_data: List of {x, y, z, timestamp} dicts.
        sample_rate: Sensor sample rate in Hz (default 20).
        wobble_threshold: RMS threshold in m/s^2.

    Returns:
        dict with keys: detected (normal/suspect/fault/unknown),
                        confidence (0–1), detail.
    """
    min_samples = int(sample_rate * 2)
    if len(accelerometer_data) < min_samples:
        return {
            "detected": "unknown",
            "confidence": 0.0,
            "detail": "Insufficient data (need >= 2 seconds)",
        }

    # Extract lateral vibration (X-axis = primary wobble signal)
    # Using raw X avoids the rectification artifact from sqrt(x²+z²)
    # which would double the dominant frequency
    lateral = [d["x"] for d in accelerometer_data]

    try:
        from scipy.signal import stft
        import numpy as np

        # STFT: window=2 seconds, overlap=50%
        nperseg = int(sample_rate * 2)  # 2-sec windows at 20Hz = 40 samples
        if nperseg > len(lateral) // 2:
            nperseg = max(len(lateral) // 2, int(sample_rate))

        f, t, Zxx = stft(
            np.array(lateral, dtype=np.float64),
            fs=sample_rate,
            nperseg=nperseg,
            noverlap=nperseg // 2,
        )

        # Magnitude spectrum
        magnitude = np.abs(Zxx)  # shape: (freq_bins, time_windows)

        # Find indices for 1–5 Hz band
        lo_idx = np.searchsorted(f, 1.0)
        hi_idx = np.searchsorted(f, 5.0)

        if hi_idx <= lo_idx:
            # Fallback: too few frequency bins
            total_rms = _rms(lateral)
            ratio = total_rms / wobble_threshold
            if ratio < 0.5:
                status, confidence = "normal", 1.0 - ratio
            elif ratio < 1.0:
                status, confidence = "suspect", ratio
            else:
                status, confidence = "fault", min(ratio / 2, 1.0)
            return {
                "detected": status,
                "confidence": round(confidence, 2),
                "detail": f"RMS vibration: {total_rms:.3f} m/s² (fallback, insufficient frequency resolution)",
            }

        # Per-window: energy in 1-5Hz band / total energy
        band_energy = np.sum(magnitude[lo_idx:hi_idx, :], axis=0)
        total_energy = np.sum(magnitude[:, :], axis=0)

        # Avoid division by zero
        safe_total = np.where(total_energy > 1e-10, total_energy, 1.0)
        energy_ratio = band_energy / safe_total  # per-window ratio

        # Persistence: fraction of windows where 1-5Hz band dominates
        high_energy_windows = np.sum(energy_ratio > 0.4)
        persistence = high_energy_windows / len(energy_ratio) if len(energy_ratio) > 0 else 0

        # Mean energy ratio in 1-5Hz band
        mean_ratio = float(np.mean(energy_ratio)) if len(energy_ratio) > 0 else 0.0

    except ImportError:
        # Fallback to RMS when scipy is not available
        total_rms = _rms(lateral)
        ratio = total_rms / wobble_threshold
        if ratio < 0.5:
            status, confidence = "normal", 1.0 - ratio
        elif ratio < 1.0:
            status, confidence = "suspect", ratio
        else:
            status, confidence = "fault", min(ratio / 2, 1.0)
        return {
            "detected": status,
            "confidence": round(confidence, 2),
            "detail": f"RMS vibration: {total_rms:.3f} m/s^2 (threshold: {wobble_threshold})",
        }

    # Classification: combine energy ratio + persistence
    if persistence > 0.6 and mean_ratio > 0.5:
        status = "fault"
        confidence = min(persistence * mean_ratio, 1.0)
        detail = (
            f"STFT: {persistence:.0%} windows with elevated 1-5Hz energy "
            f"(mean ratio: {mean_ratio:.2f}) — sustained wheel-frequency vibration"
        )
    elif persistence > 0.3 or mean_ratio > 0.25:
        status = "suspect"
        confidence = persistence * 0.6 + mean_ratio * 0.4
        detail = (
            f"STFT: {persistence:.0%} windows with elevated 1-5Hz energy "
            f"(mean ratio: {mean_ratio:.2f}) — intermittent wheel-frequency activity"
        )
    else:
        status = "normal"
        confidence = 1.0 - (persistence * 0.5 + mean_ratio * 0.5)
        detail = (
            f"STFT: {persistence:.0%} windows with elevated 1-5Hz energy "
            f"(mean ratio: {mean_ratio:.2f}) — no significant wheel-frequency vibration"
        )

    confidence = round(max(0.0, min(confidence, 1.0)), 2)

    return {"detected": status, "confidence": confidence, "detail": detail}
