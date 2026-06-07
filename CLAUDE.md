# CLAUDE.md -- bikeSharing Project Quick Reference

## Project

Shared bike fault detection platform using phone sensors.
Native Android data collector + FastAPI backend + v3.0 detection algorithms.

## Architecture

```
BicycleDataLogger (Kotlin/Android) → 传感器数据.txt + 音频.pcm + 音频_时间戳.csv
                                                      ↓
FastAPI Backend → detection_engine.py → bike_health_detector.py (v3.0)
                                                      ↓
                                           F1(Tire) + F2(Chain) + F3(Handlebar) → Health Score
                                                      ↓
                                           PostgreSQL (rides + fault_reports)
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/ml/bike_health_detector.py` | Core detection algorithm (v3.0): F1 FFT tire, F2 envelope spectrum chain, F3 gyro handlebar, composite scoring |
| `backend/app/services/detection_engine.py` | Adapter: converts API data formats to algorithm dataclasses, file parsing, unified detection entry |
| `backend/app/services/detection.py` | Orchestration: calls engine, stores results in DB |
| `backend/app/api/detection.py` | API endpoints + ECharts dashboard |
| `backend/app/models/fault_report.py` | DB model: total_score, tire/chain/handlebar scores, recommendation, details_json |
| `BicycleDataLogger/` | Native Android app (Kotlin): foreground service, 100Hz accel, 50Hz gyro, 10Hz GPS, 8kHz PCM audio |

## Data Formats

**BicycleDataLogger output:**
- `传感器数据.txt`: CSV, header row, columns: timestamp_ns, type(加速度计/陀螺仪/GPS), ax, ay, az, lat, lng, speed, course, gx, gy, gz
- `音频.pcm`: 16-bit little-endian PCM, mono, 8kHz
- `音频_时间戳.csv`: timestamp_ns, cumulative_samples

**API JSON format** (individual detection endpoints):
```json
{
  "accelerometer_data": [{"x": 0.1, "y": 0.05, "z": 9.81, "timestamp": 0.0}, ...],
  "sample_rate": 100.0
}
```

## Commands

```bash
# Start full stack
docker compose up -d

# Start infrastructure only (dev)
docker compose up -d db redis

# Backend dev server
cd backend && uvicorn app.main:app --reload --port 8000

# Tests
cd backend && pytest tests/ -v

# Specific test
cd backend && pytest tests/test_detection_engine.py -v
```

## Detection Algorithm (v3.0)

**F1 - Tire Wobble**: Z-axis accel → FFT → wheel freq f (from speed/r when GPS available) → P = A1 + 0.5*A2 → score via P_healthy=0.15, P_severe=0.60

**F2 - Chain Noise**: 8kHz audio → 2-4kHz bandpass → Hilbert envelope → lowpass 0.5-10Hz → envelope spectrum SNR at pedal freq + harmonics + phase consistency + cepstrum → anomaly score

**F3 - Handlebar**: Gyro Z-axis → straight segment selection (lowest 30% gz variance) → gz bias * 2s observation → delta_theta → score via 5°/15° thresholds

**Composite**: H = 1/(0.4/F1 + 0.3/F2 + 0.3/F3), penalty = min(F1,F2,F3)/100, S = H * penalty

## Database

- `users`: id, username, password_hash
- `rides`: id, user_id, bike_id, start_lat/lng, end_lat/lng, status
- `fault_reports`: id, ride_id, total_score, tire_score, chain_score, handlebar_score, recommendation, details_json (+ legacy detected/confidence fields)

## Dependencies

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, Redis, numpy, scipy, Jinja2
- Mobile: Kotlin, Jetpack Compose, Android SensorManager, AudioRecord, LocationManager
