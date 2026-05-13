"""Chain noise detection via audio analysis.

Abnormal chain noise presents as:
- "Clicking" at pedal-cadence frequency (~1–2 Hz per pedal stroke)
- High-frequency squealing from dry/worn chains (2–8 kHz)

Detection strategy:
1. Extract MFCC features from audio segments
2. Compute spectral centroid and zero-crossing rate for anomaly detection
3. Use threshold-based classifier (ML model upgrade later)
"""

from typing import List


def analyze_chain_noise(
    audio_features: List[float],
    noise_threshold: float = 0.5,
) -> dict:
    """Analyze audio features for chain noise anomalies.

    Args:
        audio_features: Pre-computed audio feature vector (e.g. MFCC means).
        noise_threshold: Feature magnitude threshold.

    Returns:
        dict with keys: detected, confidence, detail.
    """
    if not audio_features:
        return {
            "detected": "unknown",
            "confidence": 0.0,
            "detail": "No audio features provided",
        }

    import math

    mean_feature = sum(audio_features) / len(audio_features)
    variance = sum((f - mean_feature) ** 2 for f in audio_features) / len(audio_features)
    std_dev = math.sqrt(variance)

    # Simple anomaly score: mean + std deviation relative to threshold
    anomaly_score = (mean_feature + std_dev) / (noise_threshold * 2 + 1e-6)

    if anomaly_score < 0.5:
        status = "normal"
        confidence = 1.0 - anomaly_score
    elif anomaly_score < 1.0:
        status = "suspect"
        confidence = anomaly_score
    else:
        status = "fault"
        confidence = min(anomaly_score / 2, 1.0)

    confidence = round(max(0.0, min(confidence, 1.0)), 2)

    return {
        "detected": status,
        "confidence": confidence,
        "detail": f"Anomaly score: {anomaly_score:.3f} (mean={mean_feature:.3f}, std={std_dev:.3f})",
    }
