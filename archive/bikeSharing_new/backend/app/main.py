from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.api import auth, rides, detection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="bikeSharing — 共享单车故障智能检测平台",
    version="0.1.0",
    description="""
## 概述

基于手机传感器（加速度计、陀螺仪、麦克风）检测共享单车三大常见故障。

## 认证

除 `/api/health`、`/api/auth/register`、`/api/auth/login` 外，
所有接口需要在右上角点击 **Authorize** 并输入 Bearer Token。

Token 通过 `POST /api/auth/login` 获取。
""",
    lifespan=lifespan,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # 默认折叠 Schema
        "displayRequestDuration": True,  # 显示请求耗时
        "docExpansion": "list",          # 默认展开端点列表
        "filter": True,                  # 搜索框
    },
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证 Auth"])
app.include_router(rides.router, prefix="/api/rides", tags=["骑行管理 Rides"])
app.include_router(detection.router, prefix="/api/detection", tags=["故障检测 Detection"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
