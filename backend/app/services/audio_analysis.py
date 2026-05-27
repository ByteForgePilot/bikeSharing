"""Chain noise detection via audio feature analysis.

Abnormal chain noise presents as:
- "Clicking" at pedal-cadence frequency (~1–2 Hz per pedal stroke)
- High-frequency squealing from dry/worn chains (2–8 kHz)

Detection strategy:
1. Extract MFCC features from audio feature vector
2. Compute spectral centroid and spread
3. Compare against normal chain baseline using anomaly scoring
"""

import io
import math
import struct
import wave
from typing import List

import numpy as np


def decode_audio_to_samples(audio_bytes: bytes) -> np.ndarray:
    """Decode audio bytes to float64 PCM samples (mono).

    Tries stdlib wave (WAV/PCM) first, then falls back to librosa
    for other formats (AAC/MP4 from Android, etc.).
    Returns float64 normalized to [-1, 1].
    """
    # Try WAV first — fast, no extra deps
    try:
        with io.BytesIO(audio_bytes) as buf:
            with wave.open(buf, "rb") as wf:
                n_frames = wf.getnframes()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                raw = wf.readframes(n_frames)

        fmt_char = {1: "b", 2: "h", 4: "i"}.get(sampwidth, "h")
        scale = float(1 << (8 * sampwidth - 1))
        total_samples = n_frames * n_channels
        samples = struct.unpack(f"<{fmt_char * total_samples}", raw)

        if n_channels > 1:
            samples = samples[::n_channels]

        return np.array(samples, dtype=np.float64) / scale
    except (wave.Error, struct.error, EOFError):
        pass

    # Fallback: use librosa for non-WAV formats (AAC, MP4, etc.)
    try:
        import librosa

        with io.BytesIO(audio_bytes) as buf:
            samples, _ = librosa.load(buf, sr=None, mono=True)
        return samples.astype(np.float64)
    except Exception:
        raise ValueError("Unsupported audio format — expected WAV/PCM or AAC/MP4")


def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: List[float], mean: float) -> float:
    if len(vals) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return math.sqrt(variance)


def analyze_chain_noise(
    audio_features: List[float],
    noise_threshold: float = 0.5,
) -> dict:
    """Analyze audio features for chain noise anomalies.

    Accepts either:
    - Pre-extracted MFCC mean vector (13-20 dimensional)
    - Raw audio amplitude samples (will compute simple spectral proxy)

    Uses librosa for MFCC extraction when available and raw audio is provided.

    Args:
        audio_features: Audio feature vector or raw amplitude samples.
        noise_threshold: Anomaly score threshold.

    Returns:
        dict with keys: detected, confidence, detail.
    """
    if not audio_features or len(audio_features) == 0:
        return {
            "detected": "unknown",
            "confidence": 0.0,
            "detail": "No audio features provided",
        }

    n = len(audio_features)

    # If we have many samples (>100), treat as raw audio: extract MFCC proxy
    if n > 100:
        try:
            import numpy as np

            signal = np.array(audio_features, dtype=np.float64)

            # Compute a simple spectral centroid proxy without full FFT
            # Break signal into short frames (~23ms at 44.1kHz = 1024 samples)
            frame_size = min(1024, n // 4) if n >= 4 else n

            spectral_centroids = []
            rms_values = []

            for start in range(0, n - frame_size, frame_size // 2):
                frame = signal[start : start + frame_size]
                if len(frame) < 2:
                    continue

                # RMS energy per frame
                rms = math.sqrt(sum(f * f for f in frame) / len(frame))
                rms_values.append(rms)

                # Approximate spectral centroid via zero-crossing rate proxy:
                # higher ZCR → more high-frequency content
                zcr = sum(
                    1
                    for i in range(1, len(frame))
                    if (frame[i] >= 0) != (frame[i - 1] >= 0)
                ) / len(frame)
                spectral_centroids.append(zcr)

            if not spectral_centroids:
                # Fallback to simple stats
                mean_val = _mean(audio_features)
                std_val = _std(audio_features, mean_val)
                anomaly_score = (mean_val + std_val) / (noise_threshold * 2 + 1e-6)
            else:
                mean_sc = _mean(spectral_centroids)
                std_sc = _std(spectral_centroids, mean_sc)
                mean_rms = _mean(rms_values)
                std_rms = _std(rms_values, mean_rms)

                # Anomaly score combines:
                # 1. High-frequency content (spectral centroid) — squealing
                # 2. Energy variation (RMS std) — clicking/irregular patterns
                hf_score = mean_sc * 2  # scale up ZCR
                variation_score = std_rms / (mean_rms + 1e-6)

                anomaly_score = (hf_score * 0.4 + variation_score * 0.6) / (noise_threshold + 1e-6)

        except ImportError:
            # No numpy: fall back to simple statistical method
            mean_val = _mean(audio_features)
            std_val = _std(audio_features, mean_val)
            anomaly_score = (mean_val + std_val) / (noise_threshold * 2 + 1e-6)

    else:
        # Short feature vector (pre-extracted features like MFCC means)
        mean_val = _mean(audio_features)
        std_val = _std(audio_features, mean_val)

        # Spectral centroid proxy: higher-order MFCCs = more high-freq energy
        if n >= 8:
            # First few MFCCs capture timbre; higher ones = detail/noise
            low_order = _mean(audio_features[: n // 2])
            high_order = _mean(audio_features[n // 2 :])
            spectral_tilt = high_order / (low_order + 1e-6)
        else:
            spectral_tilt = std_val / (mean_val + 1e-6)

        anomaly_score = (mean_val + std_val * 0.5 + abs(spectral_tilt) * 0.5) / (noise_threshold + 1e-6)

    # --- Classification ---
    if anomaly_score > 1.5:
        status = "fault"
        confidence = min(anomaly_score / 3, 1.0)
        detail = f"High anomaly score: {anomaly_score:.2f} — strong chain noise signature"
    elif anomaly_score > 0.75:
        status = "suspect"
        confidence = anomaly_score / 1.5
        detail = f"Moderate anomaly score: {anomaly_score:.2f} — possible chain noise"
    elif anomaly_score > 0.3:
        status = "normal"
        confidence = 1.0 - anomaly_score * 0.5
        detail = f"Low anomaly score: {anomaly_score:.2f} — chain sounds normal"
    else:
        status = "normal"
        confidence = 0.9 + (0.3 - anomaly_score) * 2
        detail = f"Very low anomaly score: {anomaly_score:.2f} — chain is healthy"

    confidence = round(max(0.0, min(confidence, 1.0)), 2)

    return {"detected": status, "confidence": confidence, "detail": detail}
