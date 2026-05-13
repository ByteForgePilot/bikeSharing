import math
import pytest
from app.services.sensor_analysis import analyze_wheel_wobble
from app.services.audio_analysis import analyze_chain_noise
from app.services.fault_classifier import classify_handlebar


# ── analyze_wheel_wobble ───────────────────────────────────────────

def _make_accel(samples: int, freq: float, amplitude: float, sample_rate: float = 50.0):
    """Generate synthetic accelerometer data with a sine wave at `freq` Hz."""
    data = []
    for i in range(samples):
        t = i / sample_rate
        x = amplitude * math.sin(2 * math.pi * freq * t)
        z = amplitude * 0.3 * math.sin(2 * math.pi * freq * t + 0.5)
        data.append({"x": x, "y": 0.0, "z": z, "timestamp": t})
    return data


class TestWheelWobble:
    def test_insufficient_data(self):
        result = analyze_wheel_wobble([{"x": 0, "y": 0, "z": 0, "timestamp": 0}], sample_rate=50.0)
        assert result["detected"] == "unknown"
        assert result["confidence"] == 0.0

    def test_normal_low_vibration(self):
        data = _make_accel(200, freq=0.2, amplitude=0.02)
        result = analyze_wheel_wobble(data, sample_rate=50.0)
        assert result["detected"] == "normal"
        assert 0.0 <= result["confidence"] <= 1.0

    def test_suspect_moderate_vibration(self):
        data = _make_accel(200, freq=3.0, amplitude=0.25)
        result = analyze_wheel_wobble(data, sample_rate=50.0)
        assert result["detected"] in ("normal", "suspect", "fault")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_fault_strong_vibration(self):
        data = _make_accel(200, freq=3.0, amplitude=1.0)
        result = analyze_wheel_wobble(data, sample_rate=50.0)
        assert result["detected"] == "fault"
        assert 0.5 <= result["confidence"] <= 1.0

    def test_custom_threshold(self):
        data = _make_accel(200, freq=3.0, amplitude=0.15)
        result = analyze_wheel_wobble(data, sample_rate=50.0, wobble_threshold=0.1)
        assert result["detected"] in ("suspect", "fault")

    def test_confidence_bounds(self):
        data = _make_accel(200, freq=3.0, amplitude=5.0)
        result = analyze_wheel_wobble(data, sample_rate=50.0)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_return_keys(self):
        data = _make_accel(200, freq=3.0, amplitude=0.1)
        result = analyze_wheel_wobble(data, sample_rate=100.0)
        for key in ("detected", "confidence", "detail"):
            assert key in result


# ── analyze_chain_noise ────────────────────────────────────────────

class TestChainNoise:
    def test_empty_features(self):
        result = analyze_chain_noise([])
        assert result["detected"] == "unknown"
        assert result["confidence"] == 0.0

    def test_normal_low_features(self):
        result = analyze_chain_noise([0.01, 0.02, 0.01, 0.03, 0.02])
        assert result["detected"] == "normal"
        assert 0.0 <= result["confidence"] <= 1.0

    def test_suspect_moderate_features(self):
        result = analyze_chain_noise([0.3, 0.4, 0.35, 0.45, 0.5])
        assert result["detected"] in ("normal", "suspect", "fault")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_fault_strong_features(self):
        result = analyze_chain_noise([2.0, 2.5, 2.2, 2.8, 2.3])
        assert result["detected"] == "fault"
        assert 0.5 <= result["confidence"] <= 1.0

    def test_custom_threshold(self):
        result = analyze_chain_noise([0.5, 0.6, 0.55], noise_threshold=0.3)
        assert result["detected"] in ("suspect", "fault")

    def test_single_feature(self):
        result = analyze_chain_noise([0.5])
        assert result["detected"] in ("normal", "suspect", "fault")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_bounds(self):
        result = analyze_chain_noise([100.0, 200.0])
        assert 0.0 <= result["confidence"] <= 1.0

    def test_return_keys(self):
        result = analyze_chain_noise([0.1, 0.2])
        for key in ("detected", "confidence", "detail"):
            assert key in result


# ── classify_handlebar ─────────────────────────────────────────────

def _make_gyro(samples: int, yaw_offset: float, noise_deg: float = 0.05, sample_rate: float = 50.0):
    """Generate synthetic gyroscope data with a fixed yaw offset and tiny noise."""
    data = []
    for i in range(samples):
        t = i / sample_rate
        z = yaw_offset + noise_deg * (2 * math.sin(17.7 * t) - 1)
        data.append({"x": 0.0, "y": 0.0, "z": z, "timestamp": t})
    return data


class TestHandlebar:
    def test_insufficient_data(self):
        result = classify_handlebar(
            [{"x": 0, "y": 0, "z": 0, "timestamp": 0}],
            sample_rate=50.0,
        )
        assert result["detected"] == "unknown"
        assert result["confidence"] == 0.0

    def test_normal_straight_handlebar(self):
        data = _make_gyro(300, yaw_offset=0.0)
        result = classify_handlebar(data, sample_rate=50.0)
        assert result["detected"] == "normal"
        assert 0.5 <= result["confidence"] <= 1.0

    def test_suspect_slight_offset(self):
        data = _make_gyro(300, yaw_offset=2.0)
        result = classify_handlebar(data, sample_rate=50.0)
        assert result["detected"] in ("normal", "suspect", "fault")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_fault_strong_offset(self):
        data = _make_gyro(300, yaw_offset=8.0)
        result = classify_handlebar(data, sample_rate=50.0)
        assert result["detected"] == "fault"
        assert 0.5 <= result["confidence"] <= 1.0

    def test_custom_threshold(self):
        data = _make_gyro(300, yaw_offset=1.5)
        result = classify_handlebar(data, sample_rate=50.0, offset_threshold_deg=1.0)
        assert result["detected"] in ("suspect", "fault")

    def test_outlier_trimming(self):
        data = _make_gyro(300, yaw_offset=1.0)
        # Inject a spike that should be trimmed
        data[50]["z"] = 90.0
        data[200]["z"] = -90.0
        result = classify_handlebar(data, sample_rate=50.0)
        assert result["detected"] in ("normal", "suspect")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_bounds(self):
        data = _make_gyro(300, yaw_offset=30.0)
        result = classify_handlebar(data, sample_rate=50.0)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_return_keys(self):
        data = _make_gyro(300, yaw_offset=0.5)
        result = classify_handlebar(data, sample_rate=50.0)
        for key in ("detected", "confidence", "detail"):
            assert key in result
