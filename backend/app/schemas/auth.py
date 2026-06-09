"""
Pydantic Schemas
Based on need.md: backend/app/schemas/auth.py
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CaptchaResponse(BaseModel):
    """验证码响应"""
    captcha_id: str
    image_data: str  # Base64 encoded image


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    captcha_id: str
    captcha_code: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserInfo(BaseModel):
    """用户信息"""
    id: str
    username: str
    role: str
    registration_status: str
    created_at: Optional[datetime]
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    """当前用户个人资料"""
    id: str
    username: str
    role: str
    registration_status: str
    force_password_change: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    user_id: str
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    username: str = Field(..., min_length=3, max_length=100)
    captcha_id: str
    captcha_code: str = Field(..., min_length=1)


class ResetPasswordRequest(BaseModel):
    """重置密码请求（通过忘记密码流程）"""
    username: str = Field(..., min_length=3, max_length=100)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    captcha_id: str
    captcha_code: str = Field(..., min_length=1)
