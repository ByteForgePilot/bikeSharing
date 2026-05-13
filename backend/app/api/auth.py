from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    """登录成功返回的令牌"""
    access_token: str = Field(..., description="JWT 访问令牌（HS256 签名，60分钟有效）")
    token_type: str = Field(default="bearer", description="令牌类型，固定值 bearer")


class UserCreate(BaseModel):
    """注册请求"""
    username: str = Field(..., description="用户名（3~64 个字符，唯一）", min_length=3, max_length=64, examples=["testuser"])
    password: str = Field(..., description="密码（至少 4 个字符）", min_length=4, examples=["testpass"])


class UserResponse(BaseModel):
    """用户信息"""
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user_id, "username": payload.get("username", "")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Placeholder in-memory store (replace with DB in production)
_users: dict = {}
_next_id = 1


@router.post(
    "/register",
    response_model=UserResponse,
    summary="用户注册",
    description="使用用户名和密码注册新账号。密码经过 bcrypt 哈希后存储。用户名必须唯一。",
    responses={400: {"description": "用户名已存在"}},
)
async def register(user: UserCreate):
    global _next_id
    if user.username in _users:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = pwd_context.hash(user.password)
    _users[user.username] = {"id": _next_id, "username": user.username, "password": hashed}
    _next_id += 1
    return UserResponse(id=_users[user.username]["id"], username=user.username)


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="使用用户名和密码登录，返回 JWT 访问令牌。**注意：请求体格式为 `application/x-www-form-urlencoded`，不是 JSON。** 获取到的 token 需要放在后续请求的 `Authorization: Bearer <token>` 头中。",
    responses={401: {"description": "用户名或密码错误"}},
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = _users.get(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="验证 Bearer Token 并返回当前登录用户的信息。",
    responses={401: {"description": "Token 无效或已过期"}},
)
async def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(id=current_user["id"], username=current_user["username"])
