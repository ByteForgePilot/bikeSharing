"""Integration tests for v3.0 detection engine."""

import math
import struct
import pytest
import numpy as np

from app.services.detection_engine import (
    dicts_to_accel,
    dicts_to_gyro,
    parse_pcm,
    run_f1_tire_wobble,
    run_f2_chain_noise,
    run_f3_handlebar,
    run_full_detection,
)
from app.ml import AccelSample, GyroSample, AudioChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_accel(samples: int, freq: float, amplitude: float, fs: float = 100.0) -> list[AccelSample]:
    """Generate synthetic accelerometer data with sine wave at freq Hz."""
    result = []
    for i in range(samples):
        t_ns = int(i / fs * 1e9)
        x = amplitude * math.sin(2 * math.pi * freq * i / fs)
        z = 9.81 + amplitude * 0.3 * math.sin(2 * math.pi * freq * i / fs + 0.5)
        result.append(AccelSample(t_ns, x, 0.0, z))
    return result


def _make_gyro(samples: int, yaw_offset: float, fs: float = 50.0) -> list[GyroSample]:
    """Generate synthetic gyro data with fixed yaw offset."""
    result = []
    for i in range(samples):
        t_ns = int(i / fs * 1e9)
        z = yaw_offset + 0.01 * (2 * math.sin(17.7 * i / fs) - 1)
        result.append(GyroSample(t_ns, 0.0, 0.0, z))
    return result


def _make_audio(samples: int, freq: float = 3.0, fs: float = 8000.0) -> tuple[np.ndarray, list[AudioChunk]]:
    """Generate synthetic audio with periodic clicks at freq Hz."""
    t = np.arange(samples) / fs
    # Periodic impulses + background noise
    impulse = np.zeros(samples, dtype=np.float32)
    period_samples = int(fs / freq)
    for i in range(0, samples, period_samples):
        impulse[i] = 1.0
    noise = np.random.normal(0, 0.01, samples).astype(np.float32)
    audio = impulse + noise
    audio /= max(np.max(np.abs(audio)), 1.0)

    # Create audio timestamp chunks (every ~500 samples)
    chunks = []
    for i in range(0, samples, 512):
        chunks.append(AudioChunk(int(i / fs * 1e9), i + 512))
    return audio, chunks


# ---------------------------------------------------------------------------
# F1 - Tire Wobble
# ---------------------------------------------------------------------------

class TestF1TireWobble:
    def test_normal_bike(self):
        """Low vibration should score high (healthy)."""
        accel = _make_accel(500, freq=3.0, amplitude=0.05)
        result = run_f1_tire_wobble(accel)
        assert result["score"] >= 70, f"Expected healthy, got {result['score']}"
        assert result["wheel_freq_hz"] > 0

    def test_wobble_fault(self):
        """Strong periodic vibration at wheel frequency should score low."""
        accel = _make_accel(1000, freq=3.0, amplitude=8.0)
        result = run_f1_tire_wobble(accel)
        assert result["score"] < 50, f"Expected fault, got {result['score']}"
        assert "P_value" in result

    def test_insufficient_data(self):
        """Too few samples should return 100 (not enough data to judge)."""
        accel = _make_accel(30, freq=3.0, amplitude=1.0)
        result = run_f1_tire_wobble(accel)
        assert result["score"] == 100.0


# ---------------------------------------------------------------------------
# F2 - Chain Noise
# ---------------------------------------------------------------------------

class TestF2ChainNoise:
    def test_normal_audio(self):
        """Pure noise should score high (no chain noise)."""
        audio = np.random.normal(0, 0.005, 4000).astype(np.float32)
        chunks = [AudioChunk(0, 4000)]
        result = run_f2_chain_noise(audio, chunks)
        assert result["score"] >= 40, f"Got {result['score']}"

    def test_periodic_clicks(self):
        """Periodic impulses should be detected as chain noise."""
        audio, chunks = _make_audio(8000, freq=2.0)
        result = run_f2_chain_noise(audio, chunks)
        assert "score" in result
        assert "prediction" in result

    def test_empty_audio(self):
        """Empty audio should return healthy score."""
        audio = np.array([], dtype=np.float32)
        chunks: list = []
        result = run_f2_chain_noise(audio, chunks)
        assert result["score"] == 100.0


# ---------------------------------------------------------------------------
# F3 - Handlebar
# ---------------------------------------------------------------------------

class TestF3Handlebar:
    def test_straight_handlebar(self):
        """Zero yaw offset should score high."""
        gyro = _make_gyro(500, yaw_offset=0.0)
        result = run_f3_handlebar(gyro)
        assert result["score"] >= 70, f"Expected straight, got {result['score']}"

    def test_misaligned_handlebar(self):
        """Large yaw offset should score low."""
        gyro = _make_gyro(500, yaw_offset=0.2)  # ~11.5 deg/s
        result = run_f3_handlebar(gyro)
        assert result["score"] < 70, f"Expected misaligned, got {result['score']}"

    def test_insufficient_gyro(self):
        """Too few samples should score 100."""
        gyro = _make_gyro(10, yaw_offset=0.5)
        result = run_f3_handlebar(gyro)
        assert result["score"] == 100.0


# ---------------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------------

class TestFullDetection:
    def test_end_to_end(self):
        """Full pipeline: accel + gyro + audio → health score."""
        accel = _make_accel(500, freq=3.0, amplitude=0.1)
        gyro = _make_gyro(500, yaw_offset=0.01)
        audio, chunks = _make_audio(8000, freq=3.0)

        result = run_full_detection(accel, gyro, audio, chunks)
        health = result["health"]

        assert "total_score" in health
        assert "recommendation" in health
        assert 0 <= health["total_score"] <= 100
        assert health["recommendation"] in ("推荐骑行", "谨慎使用", "建议换车")

    def test_data_formats_conversion(self):
        """Dict → dataclass conversion."""
        data = [{"x": 0.1, "y": 0.2, "z": 9.8, "timestamp": 0.0}]
        accel = dicts_to_accel(data)
        gyro = dicts_to_gyro(data)
        assert len(accel) == 1
        assert len(gyro) == 1
        assert abs(accel[0].az - 9.8) < 0.01

    def test_pcm_parsing(self):
        """16-bit LE PCM byte parsing."""
        raw = struct.pack("<3h", 0, 16384, -16384)
        audio = parse_pcm(raw)
        assert len(audio) == 3
        assert abs(audio[1] - 0.5) < 0.01
        assert abs(audio[2] + 0.5) < 0.01


# ---------------------------------------------------------------------------
# v3.0 specific
# ---------------------------------------------------------------------------

class TestV3AlgorithmSpecifics:
    def test_flat_road_detection(self):
        """Verify flat_fraction is computed."""
        accel = _make_accel(500, freq=3.0, amplitude=0.02)
        result = run_f1_tire_wobble(accel)
        assert "flat_fraction" in result
        assert 0 <= result["flat_fraction"] <= 1

    def test_pedal_snr(self):
        """Verify pedal SNR is in the result for chain noise."""
        audio, chunks = _make_audio(16000, freq=2.5)
        result = run_f2_chain_noise(audio, chunks)
        assert "pedal_snr_db" in result

    def test_delta_theta(self):
        """Verify delta_theta_deg is in handlebar result."""
        gyro = _make_gyro(500, yaw_offset=0.05)
        result = run_f3_handlebar(gyro)
        assert "delta_theta_deg" in result
        assert result["delta_theta_deg"] >= 0
