# Repository Guidelines

## Project Structure

`
bikrsharing/
├── BicycleDataLogger/          # Native Android data collector (Kotlin, Jetpack Compose)
│   └── app/src/main/java/com/bicycle/datalogger/
│       ├── sensors/            # AccelCollector, GyroCollector, GpsCollector, AudioCollector, SensorService
│       └── ui/screens/         # Compose UI
├── data/                       # Real sensor data + standalone detection runner
│   ├── 传感器数据.txt            # Accelerometer + gyroscope + GPS CSV
│   ├── 音频.pcm                  # 16-bit LE PCM audio
│   ├── 音频_时间戳.csv            # Audio timestamp mapping
│   └── run_detection.py         # Standalone detection script (no server needed)
├── backend/
│   └── app/
│       ├── api/                # FastAPI route handlers (auth, rides, detection)
│       ├── core/               # JWT security
│       ├── ml/                 # Detection algorithm v3.0 (bike_health_detector.py)
│       ├── models/             # SQLAlchemy ORM (User, Ride, FaultReport)
│       ├── repositories/       # DB access layer
│       ├── schemas/            # Pydantic request/response models
│       ├── services/           # Business logic + detection engine adapter
│       └── templates/          # ECharts dashboard HTML (Jinja2)
│   └── tests/                  # pytest (test_detection_engine, test_api, test_rides_db)
├── docs/                       # Project documentation (00-09)
├── docker-compose.yml          # PostgreSQL + Redis + Backend
└── AGENTS.md                   # This file
`

## Build, Test, and Development Commands

`ash
# Full stack (Docker)
docker compose up -d                            # db + redis + backend on :8000

# Local backend dev (standalone mode, no Docker/DB)
cd backend
python -m uvicorn app.main:app --reload --port 8000   # Dashboard + /process endpoint
                                                       # DB endpoints error gracefully

# Install dependencies
cd backend && pip install -r requirements.txt

# Run detection on real data (no server needed)
cd E:\Project\personal\bikrsharing
python data/run_detection.py                          # Reads data/ files, prints + saves JSON

# Run tests
cd backend && pytest tests/ -v                          # All tests
cd backend && pytest tests/test_detection_engine.py -v   # Detection engine only
cd backend && pytest tests/test_api.py -v                # API integration

# Android build
cd BicycleDataLogger && ./gradlew assembleDebug
`

## Coding Style & Naming

- **Python**: 4-space indentation. Follow PEP 8. Type hints for function signatures.
- **Python encoding**: All .py files must be UTF-8 **without BOM**. Avoid UTF-16LE (causes "null bytes" SyntaxError).
- **Kotlin**: Standard Kotlin conventions. 4-space indentation.
- **File naming**: snake_case for Python modules, PascalCase for Kotlin classes.
- **DB columns**: snake_case matching SQLAlchemy ORM attributes.
- No formatter or linter enforced at this stage.

## Testing Guidelines

- Framework: pytest with pytest-asyncio for async tests.
- Test files: 	ests/test_<module>.py.
- Test classes: Test<Feature> grouping related cases.
- Coverage focus: detection engine (F1/F2/F3 pipelines), API endpoints, DB operations.
- Minimum data: synthetic sensor data (_make_accel, _make_gyro, _make_audio helpers).

## Commit & PR Guidelines

- Commit messages: Chinese or English. Format: <version/tag>: <summary> (e.g., 2.0: Integrate algorithm v3.0).
- Keep commits focused — one logical change per commit.
- PRs should include: a brief description of changes, any new dependencies, and test results.
- Link related issues when applicable.

## Architecture Notes

- **Detection pipeline**: BicycleDataLogger -> CSV/PCM files -> POST /api/detection/upload/{ride_id} -> detection_engine.py -> ike_health_detector.py (v3.0) -> FaultReport in PostgreSQL.
- **Standalone mode**: Backend starts without PostgreSQL/Redis. /api/detection/dashboard and /api/detection/process work independently. The process endpoint uses pp.services.detection_engine directly, not the DB layer.
- **data/run_detection.py**: Runs full detection (F1/F2/F3 + composite score) on local sensor data without any server infrastructure. Results saved to data/detection_result.json.
- **Dashboard**: Served at /api/detection/dashboard via Jinja2 Environment + ECharts. Template directory is pp/templates (relative to ackend/).
- **Scoring**: Three sub-scores (0-100) combined via weighted harmonic mean with minimum penalty factor ("barrel effect").
- **Auth**: JWT-based. Auto-registration on first launch with device ID.

## Known Issues

- **File encoding**: Source .py files must be UTF-8 without BOM. Some files were originally saved as UTF-16LE (causes "null bytes" SyntaxError). Use git show HEAD:<file> to restore originals if encoding issues arise.
- **Network-dependent builds**: Docker builds require internet for pip install; corporate firewalls may block PyPI. Use python -m uvicorn (local) and python data/run_detection.py as alternatives.
- **Dashboard template path**: When running uvicorn from ackend/, the template directory must be pp/templates (relative path, not ackend/app/templates).

## Security & Configuration

- Copy .env.example to .env for local overrides (defaults work for Docker).
- SECRET_KEY must be changed before production deployment.
- API endpoints require Bearer token except /api/health, /api/auth/*, /api/detection/dashboard, and /api/detection/process.
- Never commit .env or credentials.