from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import create_access_token, get_current_user
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services import auth as auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    summary="用户注册",
    description="使用用户名和密码注册新账号。密码经过 bcrypt 哈希后存储。用户名必须唯一。",
    responses={400: {"description": "用户名已存在"}},
)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_user = await auth_service.register_user(db, user.username, user.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(id=db_user.id, username=db_user.username)


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="使用用户名和密码登录，返回 JWT 访问令牌。",
    responses={401: {"description": "用户名或密码错误"}},
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="验证 Bearer Token 并返回当前登录用户的信息。",
    responses={401: {"description": "Token 无效或已过期"}},
)
async def me(current_user=Depends(get_current_user)):
    return UserResponse(id=current_user.id, username=current_user.username)
