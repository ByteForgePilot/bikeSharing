# Repository Guidelines

## Project Structure

```
bikrsharing/
├── BicycleDataLogger/          # Native Android data collector (Kotlin, Jetpack Compose)
│   └── app/src/main/java/com/bicycle/datalogger/
│       ├── sensors/            # AccelCollector, GyroCollector, GpsCollector, AudioCollector, SensorService
│       └── ui/screens/         # Compose UI
├── backend/
│   └── app/
│       ├── api/                # FastAPI route handlers (auth, rides, detection)
│       ├── core/               # JWT security
│       ├── ml/                 # Detection algorithm v3.0 (bike_health_detector.py)
│       ├── models/             # SQLAlchemy ORM (User, Ride, FaultReport)
│       ├── repositories/       # DB access layer
│       ├── schemas/            # Pydantic request/response models
│       ├── services/           # Business logic + detection engine adapter
│       └── templates/          # ECharts dashboard HTML
│   └── tests/                  # pytest (test_detection_engine, test_api, test_rides_db)
├── docs/                       # Project documentation (00-09)
├── docker-compose.yml          # PostgreSQL + Redis + Backend
└── AGENTS.md
```

## Build, Test, and Development Commands

```bash
# Full stack (Docker)
docker compose up -d                          # db + redis + backend on :8000

# Infrastructure only (local backend dev)
docker compose up -d db redis
cd backend && uvicorn app.main:app --reload --port 8000

# Install dependencies
cd backend && pip install -r requirements.txt

# Run tests
cd backend && pytest tests/ -v                          # All tests
cd backend && pytest tests/test_detection_engine.py -v   # Detection engine only
cd backend && pytest tests/test_api.py -v                # API integration

# Android build
cd BicycleDataLogger && ./gradlew assembleDebug
```

## Coding Style & Naming

- **Python**: 4-space indentation. Follow PEP 8. Type hints for function signatures.
- **Kotlin**: Standard Kotlin conventions. 4-space indentation.
- **File naming**: snake_case for Python modules, PascalCase for Kotlin classes.
- **DB columns**: snake_case matching SQLAlchemy ORM attributes.
- No formatter or linter enforced at this stage.

## Testing Guidelines

- Framework: `pytest` with `pytest-asyncio` for async tests.
- Test files: `tests/test_<module>.py`.
- Test classes: `Test<Feature>` grouping related cases.
- Coverage focus: detection engine (F1/F2/F3 pipelines), API endpoints, DB operations.
- Minimum data: synthetic sensor data (`_make_accel`, `_make_gyro`, `_make_audio` helpers).

## Commit & PR Guidelines

- Commit messages: Chinese or English. Format: `<version/tag>: <summary>` (e.g., `v2.0: Integrate algorithm v3.0`).
- Keep commits focused — one logical change per commit.
- PRs should include: a brief description of changes, any new dependencies, and test results.
- Link related issues when applicable.

## Architecture Notes

- **Detection pipeline**: BicycleDataLogger → CSV/PCM files → `POST /api/detection/upload/{ride_id}` → `detection_engine.py` → `bike_health_detector.py` (v3.0) → `FaultReport` in PostgreSQL.
- **Scoring**: Three sub-scores (0-100) combined via weighted harmonic mean with minimum penalty factor ("barrel effect").
- **Dashboard**: Served at `/api/detection/dashboard` via Jinja2 + ECharts.
- **Auth**: JWT-based. Auto-registration on first launch with device ID.

## Security & Configuration

- Copy `.env.example` to `.env` for local overrides (defaults work for Docker).
- `SECRET_KEY` must be changed before production deployment.
- API endpoints require Bearer token except `/api/health`, `/api/auth/*`, and `/api/detection/process`.
- Never commit `.env` or credentials.
