from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="JWT 访问令牌（HS256 签名，60分钟有效）")
    token_type: str = Field(default="bearer", description="令牌类型，固定值 bearer")


class UserCreate(BaseModel):
    username: str = Field(..., description="用户名（3~64 个字符，唯一）", min_length=3, max_length=64, examples=["testuser"])
    password: str = Field(..., description="密码（至少 4 个字符）", min_length=4, examples=["testpass"])


class UserResponse(BaseModel):
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
