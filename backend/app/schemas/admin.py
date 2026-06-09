"""
Admin Schemas
Based on need.md: backend/app/schemas/admin.py
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    role: str
    registration_status: str
    force_password_change: bool
    created_at: Optional[datetime]
    last_login_at: Optional[datetime]


class UserReviewRequest(BaseModel):
    """用户审核请求"""
    approved: bool
    reason: Optional[str] = None


class PasswordResetReviewRequest(BaseModel):
    """密码重置审核请求"""
    approved: bool
    reason: Optional[str] = None


class PendingUser(BaseModel):
    """待审核用户"""
    id: str
    username: str
    created_at: datetime
    registration_status: str


class PendingUserList(BaseModel):
    """待审核用户列表"""
    total: int
    users: List[PendingUser]


class PendingPasswordReset(BaseModel):
    """待审核密码重置"""
    id: str
    user_id: str
    username: str
    requested_at: datetime
    ip_address: Optional[str] = None


class PendingPasswordResetList(BaseModel):
    """待审核密码重置列表"""
    total: int
    requests: List[PendingPasswordReset]


class AdminNotification(BaseModel):
    """管理员通知"""
    id: str
    type: str
    title: str
    message: str
    data: Optional[dict]
    created_at: datetime
    read: bool = False
