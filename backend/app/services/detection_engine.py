"""
Detection engine adapter --- bridges API data formats to the v3.0 algorithm.

Accepts two input paths:
  1. In-memory sensor data (from JSON API) ── converted to AccelSample/GyroSample lists
  2. Uploaded files (传感器数据.txt / 音频.pcm / 音频_时间戳.csv) ── parsed in-memory
Both paths feed into bike_health_detector.py for the three-level fault detection
and composite health scoring.
"""

from __future__ import annotations

import io
import struct
from typing import List

import numpy as np

from app.ml import (
    AccelSample,
    AudioChunk,
    GyroSample,
    compute_health_score,
    detect_chain_noise,
    detect_handlebar_misalignment,
    detect_tire_wobble,
    select_analysis_window,
)


# ---------------------------------------------------------------------------
# Path A ── JSON API: convert dicts to algorithm dataclasses
# ---------------------------------------------------------------------------

def dicts_to_accel(data: List[dict]) -> list[AccelSample]:
    """Convert [{x,y,z,timestamp}, ...] to [AccelSample, ...]."""
    return [
        AccelSample(int(d["timestamp"] * 1e9), d["x"], d["y"], d["z"]) for d in data
    ]


def dicts_to_gyro(data: List[dict]) -> list[GyroSample]:
    """Convert [{x,y,z,timestamp}, ...] to [GyroSample, ...]."""
    return [
        GyroSample(int(d["timestamp"] * 1e9), d["x"], d["y"], d["z"]) for d in data
    ]


# ---------------------------------------------------------------------------
# Path B ── File upload: parse CSV / PCM in memory
# ---------------------------------------------------------------------------

def parse_sensor_csv(text: str) -> tuple[list[AccelSample], list[GyroSample]]:
    """Parse BicycleDataLogger''s 传感器数据.txt (CSV, header row skipped)."""
    accel: list[AccelSample] = []
    gyro: list[GyroSample] = []
    for line in text.strip().split("\n")[1:]:
        parts = line.strip().split(",")
        if len(parts) < 12:
            continue
        ts = int(parts[0])
        stype = parts[1].strip()
        if stype == "加速度计":
            accel.append(AccelSample(ts, float(parts[2]), float(parts[3]), float(parts[4])))
        elif stype == "陀螺仪":
            gyro.append(GyroSample(ts, float(parts[9]), float(parts[10]), float(parts[11])))
    return accel, gyro


def parse_pcm(raw: bytes) -> np.ndarray:
    """Parse 16-bit little-endian PCM → float32 [-1, 1]."""
    n = len(raw) // 2
    samples = struct.unpack(f"<{n}h", raw)
    return np.array(samples, dtype=np.float32) / 32768.0


def parse_audio_ts(text: str) -> list[AudioChunk]:
    """Parse 音频_时间戳.csv (timestamp_ns, cumulative_samples)."""
    chunks: list[AudioChunk] = []
    for line in text.strip().split("\n")[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            chunks.append(AudioChunk(int(parts[0]), int(parts[1])))
    return chunks


def parse_audio_bytes(audio_bytes: bytes) -> np.ndarray:
    """Try to decode audio bytes (WAV or raw PCM 16-bit LE)."""
    # First try as WAV via wave module
    try:
        import wave
        with io.BytesIO(audio_bytes) as buf:
            with wave.open(buf, "rb") as wf:
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
        fmt_char = {1: "b", 2: "h", 4: "i"}.get(wf.getsampwidth(), "h")
        scale = float(1 << (8 * wf.getsampwidth() - 1))
        samples = struct.unpack(f"<{fmt_char * n_frames}", raw)
        return np.array(samples, dtype=np.float32) / scale
    except Exception:
        pass

    # Fallback: raw 16-bit LE PCM
    return parse_pcm(audio_bytes)


# ---------------------------------------------------------------------------
# Unified detection entry points
# ---------------------------------------------------------------------------

def run_f1_tire_wobble(
    accel_data: list[AccelSample],
    gyro_data: list[GyroSample] | None = None,
    speed_ms: float | None = None,
) -> dict:
    """Run F1 tire wobble detection."""
    return detect_tire_wobble(accel_data, gyro_data, speed_ms)


def run_f2_chain_noise(
    audio: np.ndarray,
    audio_chunks: list[AudioChunk],
    pedal_freq_hz: float | None = None,
) -> dict:
    """Run F2 chain noise detection."""
    return detect_chain_noise(audio, audio_chunks, pedal_freq_hz)


def run_f3_handlebar(gyro_data: list[GyroSample]) -> dict:
    """Run F3 handlebar misalignment detection."""
    return detect_handlebar_misalignment(gyro_data)


def run_full_detection(
    accel: list[AccelSample],
    gyro: list[GyroSample],
    audio: np.ndarray,
    audio_ts: list[AudioChunk],
) -> dict:
    """Run all three detections + composite health score.

    Returns a dict with f1, f2, f3 results and the composite health score.
    """
    # Adaptive window selection for long recordings
    window_result = select_analysis_window(accel, gyro, audio, audio_ts)
    accel_s = window_result["accel_slice"]
    gyro_s = window_result["gyro_slice"]
    audio_s = window_result["audio_slice"]
    audio_ts_s = window_result["audio_ts_slice"]

    f1 = detect_tire_wobble(accel_s, gyro_s)
    f2 = detect_chain_noise(audio_s, audio_ts_s, pedal_freq_hz=f1["wheel_freq_hz"])
    f3 = detect_handlebar_misalignment(gyro_s)
    health = compute_health_score(f1, f2, f3)

    return {
        "health": health,
        "f1": f1,
        "f2": f2,
        "f3": f3,
        "window_used": window_result["used_window"],
        "data_summary": {
            "accel_count": len(accel_s),
            "gyro_count": len(gyro_s),
            "audio_samples": int(len(audio_s)),
            "audio_ts_blocks": len(audio_ts_s),
        },
    }
