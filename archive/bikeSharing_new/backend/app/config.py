from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "bikeSharing API"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bikesharing"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/bikesharing"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Sensor data
    SENSOR_SAMPLE_RATE: int = 50        # Hz, accelerometer/gyroscope
    AUDIO_SAMPLE_RATE: int = 44100      # Hz
    MAX_RIDE_DURATION_SECONDS: int = 3600

    model_config = {"env_file": ".env"}


settings = Settings()
