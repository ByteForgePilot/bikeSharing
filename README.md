# bikeSharing -- Shared Bike Fault Detection Platform

Mobile sensor-based shared bike fault detection: ride, collect sensor data, get instant health scores.

## Architecture

```
BicycleDataLogger (Android)
    Accel 100Hz + Gyro 50Hz + GPS 10Hz + Audio 8kHz PCM
        |
        |  POST /api/detection/upload/{ride_id}  (sensor CSV + PCM + timestamps)
        v
FastAPI Backend  (port 8000)
    |
    +-- /api/auth/*           JWT authentication
    +-- /api/rides/*          Ride lifecycle (start/end/data)
    +-- /api/detection/upload Full 3-level detection
    +-- /api/detection/*      Individual fault endpoints
    +-- /api/detection/dashboard   ECharts web dashboard
    |
    v
Detection Engine (v3.0)
    F1: Tire Wobble     -- FFT + wheel-frequency analysis
    F2: Chain Noise     -- Envelope spectrum + cepstrum
    F3: Handlebar       -- Gyro yaw bias + straight-segment
    Composite: Weighted harmonic mean + penalty factor (0-100)
    |
    v
PostgreSQL + Redis
```

## Quick Start

### 1. Docker (recommended)

```bash
cp .env.example .env      # optional, defaults work
docker compose up -d       # db + redis + backend on port 8000
```

The backend auto-creates database tables on first start. Dashboard at http://localhost:8000/api/detection/dashboard.

### 2. Local Development

```bash
# Start infrastructure only
docker compose up -d db redis

# Install backend deps
cd backend
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --port 8000
```


### 3. Standalone Mode (No Docker)

`ash
# Backend starts without PostgreSQL/Redis
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Only these endpoints are available without DB:
#   GET  /api/detection/dashboard   -- ECharts dashboard
#   POST /api/detection/process     -- File upload detection (no auth)

# DB-requiring endpoints (auth, rides, upload) will fail gracefully.
`

### 4. Run Detection on Local Sensor Data

`ash
# No server needed -- runs detection directly on data/ files
cd E:\Project\personal\bikrsharing
python data/run_detection.py

# Reads data/�的传感器数据.txt + 音频.pcm + 音频_时间戳.csv
# Runs F1/F2/F3 + composite health score
# Saves detailed results to data/detection_result.json
`

The data/ directory contains real sensor data collected by BicycleDataLogger, ready for testing the detection pipeline.
### 3. Mobile Data Collection

Open `BicycleDataLogger/` in Android Studio, build and install the APK. The app collects:
- Accelerometer @ 100Hz
- Gyroscope @ 50Hz
- GPS @ 10Hz (with network location fallback)
- Audio @ 8kHz 16-bit PCM mono

Ride data is saved to `Documents/自行车数据/<timestamp>/` as three files:
- `传感器数据.txt` -- CSV: timestamp_ns, sensor_type, ax, ay, az, lat, lng, speed, course, gx, gy, gz
- `音频.pcm` -- 16-bit little-endian PCM
- `音频_时间戳.csv` -- timestamp_ns, cumulative_samples

Upload these three files to `POST /api/detection/upload/{ride_id}` for full analysis.

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register device account |
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/rides/start` | Start a ride |
| POST | `/api/rides/{id}/end` | End a ride |
| POST | `/api/rides/{id}/sensor-data` | Upload sensor readings |
| POST | `/api/rides/{id}/audio` | Upload audio for chain detection |
| POST | `/api/detection/upload/{id}` | Upload BicycleDataLogger files for full detection |
| POST | `/api/detection/process` | Standalone file-upload detection (no auth) |
| GET | `/api/detection/report/{id}` | Get detection report |
| GET | `/api/detection/health-score/{id}` | Get composite health score |
| GET | `/api/detection/dashboard` | Web visualization dashboard |

Full Swagger docs at http://localhost:8000/docs.

## Detection System (v3.0)

Three-fault detection using the phone''s built-in sensors:

1. **F1 Tire Wobble** -- FFT analysis of Z-axis acceleration. Extracts wheel rotation frequency and computes wobble characteristic P = A1 + 0.5*A2. Uses flat-road window selection for reliable readings.

2. **F2 Chain Noise** -- Envelope spectrum analysis of 8kHz audio. Hilbert transform extracts pedal-frequency envelope, SNR + harmonic detection + cepstrum periodic analysis identify chain-specific impacts vs environmental noise.

3. **F3 Handlebar Misalignment** -- Gyro Z-axis yaw bias detection. Selects straight-riding segments (lowest gz variance windows) and computes equivalent steering offset angle.

**Composite scoring**: Weighted harmonic mean (0.4/0.3/0.3) with minimum penalty factor ("barrel effect" -- a single severe fault pulls down the overall score).

| Score | Level | Recommendation |
|-------|-------|----------------|
| >= 70 | Good | 推荐骑行 |
| 50-69 | Caution | 谨慎使用 |
| < 50 | Bad | 建议换车 |

## Project Structure

```
bikrsharing/
+-- data/                  Real sensor data + detection runner
|   +-- run_detection.py   Standalone detection script (no server)
|   +-- 传感器数据.txt        Accelerometer/gyro/GPS CSV
|   +-- 音频.pcm              16-bit LE PCM audio
|   +-- 音频_时间戳.csv         Audio timestamp mapping
+-- BicycleDataLogger/     Native Android data collection app (Kotlin)
+-- backend/
|   +-- app/
|   |   +-- api/           FastAPI route handlers
|   |   +-- core/          JWT security
|   |   +-- ml/            Detection algorithm v3.0
|   |   +-- models/        SQLAlchemy ORM models
|   |   +-- repositories/  Database access layer
|   |   +-- schemas/       Pydantic request/response schemas
|   |   +-- services/      Business logic + detection engine
|   |   +-- templates/     ECharts dashboard HTML
|   +-- tests/
+-- docs/                  Project documentation
+-- docker-compose.yml     Docker orchestration
```

## Testing

```bash
cd backend
pytest tests/test_detection_engine.py -v    # Detection algorithm tests
pytest tests/test_api.py -v                  # API integration tests
pytest tests/test_rides_db.py -v             # Database tests
```
