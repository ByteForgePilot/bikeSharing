from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, rides, detection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB, load ML models, etc.
    yield
    # Shutdown: cleanup


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(rides.router, prefix="/api/rides", tags=["Rides"])
app.include_router(detection.router, prefix="/api/detection", tags=["Detection"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
