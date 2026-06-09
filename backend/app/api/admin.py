"""
Admin API - User Management & Review
Based on need.md: backend/app/api/admin.py
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update
from typing import List, Optional
from app.database import get_db
from app.core.deps import require_admin_user
from app.models import ModelBackend, User, PasswordResetRequest
from app.core.security import get_password_hash
from app.services.audit_service import record_audit_event
from app.utils.notification import notification_service
from app.schemas.admin import (
    UserResponse, 
    UserReviewRequest, 
    PasswordResetReviewRequest,
    PendingUserList,
    PendingPasswordResetList,
    AdminNotification
)

router = APIRouter(prefix="/api/admin", tags=["管理员"], dependencies=[Depends(require_admin_user)])


@router.get("/overview")
async def get_admin_overview(db: AsyncSession = Depends(get_db)):
    """获取管理端概览聚合数据，避免前端拉全量列表再统计。"""
    total_users = await db.scalar(select(func.count()).select_from(User))
    admin_users = await db.scalar(select(func.count()).select_from(User).where(User.role == "admin"))
    pending_users = await db.scalar(select(func.count()).select_from(User).where(User.registration_status == "pending_review"))
    pending_resets = await db.scalar(select(func.count()).select_from(PasswordResetRequest).where(PasswordResetRequest.status == "pending"))
    model_backends = await db.scalar(select(func.count()).select_from(ModelBackend))
    return {
        "total_users": total_users or 0,
        "admin_users": admin_users or 0,
        "pending_users": pending_users or 0,
        "pending_resets": pending_resets or 0,
        "model_backends": model_backends or 0,
    }


# ===== 用户管理 =====

@router.get("/users/pending", response_model=PendingUserList)
async def get_pending_users(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取待审核用户列表"""
    result = await db.execute(
        select(User).where(
            User.registration_status == "pending_review"
        ).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    
    return {
        "total": len(users),
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "created_at": u.created_at,
                "registration_status": u.registration_status
            }
            for u in users
        ]
    }


@router.post("/users/{user_id}/review")
async def review_user(
    user_id: str,
    review: UserReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_user),
):
    """审核用户注册申请"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.registration_status != "pending_review":
        raise HTTPException(status_code=400, detail="该用户已审核")
    
    # 更新状态
    new_status = "active" if review.approved else "disabled"
    user.registration_status = new_status
    await db.commit()
    await record_audit_event(
        db,
        "user_review",
        current_admin.id,
        resource_type="user",
        resource_id=user_id,
        details={"approved": review.approved, "status": new_status, "username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    notification_service.broadcast_to_admins({
        "type": "user_updated",
        "title": "用户审核已处理",
        "message": f"用户 {user.username} 已{'通过' if review.approved else '拒绝'}审核",
        "data": {"user_id": str(user.id), "username": user.username, "status": new_status},
        "priority": "low",
    })
    
    # 发送通知给用户
    notification = notification_service.create_approval_result_notification(
        str(user.id),
        review.approved,
        "registration"
    )
    notification_service.send_notification(str(user.id), notification)
    
    return {
        "message": "审核通过" if review.approved else "审核拒绝",
        "user_id": user_id,
        "status": new_status
    }


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    status: Optional[str] = None,
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表（支持筛选）"""
    query = select(User)
    
    if status:
        query = query.where(User.registration_status == status)
    if role:
        query = query.where(User.role == role)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "role": u.role,
            "registration_status": u.registration_status,
            "force_password_change": u.force_password_change,
            "created_at": u.created_at,
            "last_login_at": u.last_login_at
        }
        for u in users
    ]


# ===== 密码重置审核 =====

@router.get("/password-resets/pending", response_model=PendingPasswordResetList)
async def get_pending_password_resets(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取待审核密码重置列表"""
    result = await db.execute(
        select(PasswordResetRequest, User.username)
        .join(User, PasswordResetRequest.user_id == User.id)
        .where(PasswordResetRequest.status == "pending")
        .offset(skip).limit(limit)
    )
    requests = result.all()
    
    return {
        "total": len(requests),
        "requests": [
            {
                "id": str(r.PasswordResetRequest.id),
                "user_id": str(r.PasswordResetRequest.user_id),
                "username": r.username,
                "requested_at": r.PasswordResetRequest.requested_at,
                "ip_address": str(r.PasswordResetRequest.ip_address)
            }
            for r in requests
        ]
    }


@router.post("/password-resets/{request_id}/review")
async def review_password_reset(
    request_id: str,
    review: PasswordResetReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_user),
):
    """审核密码重置申请"""
    result = await db.execute(
        select(PasswordResetRequest).where(PasswordResetRequest.id == request_id)
    )
    reset_request = result.scalar_one_or_none()
    
    if not reset_request:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    if reset_request.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")
    
    # 更新状态
    new_status = "approved" if review.approved else "rejected"
    reset_request.status = new_status
    
    if review.approved:
        # 不生成临时密码，只标记为通过
        now = datetime.now(timezone.utc)
        reset_request.reviewed_at = now
        reset_request.expires_at = now + timedelta(minutes=10)  # 10分钟内有效
        await db.commit()
        await record_audit_event(
            db,
            "password_reset_review",
            current_admin.id,
            resource_type="password_reset",
            resource_id=request_id,
            details={"approved": True, "user_id": str(reset_request.user_id)},
            ip_address=request.client.host if request.client else None,
        )
        
        # 发送通知给用户，告知可以设置新密码
        notification = notification_service.create_approval_result_notification(
            str(reset_request.user_id),
            True,
            "password_reset"
        )
        notification_service.send_notification(str(reset_request.user_id), notification)
        
        return {
            "message": "审核通过",
            "request_id": request_id,
            "note": "用户现在可以通过忘记密码流程设置新密码"
        }
    else:
        await db.commit()
        await record_audit_event(
            db,
            "password_reset_review",
            current_admin.id,
            resource_type="password_reset",
            resource_id=request_id,
            details={"approved": False, "user_id": str(reset_request.user_id)},
            ip_address=request.client.host if request.client else None,
        )
        
        # 发送拒绝通知
        notification = notification_service.create_approval_result_notification(
            str(reset_request.user_id),
            False,
            "password_reset"
        )
        notification_service.send_notification(str(reset_request.user_id), notification)
        
        return {
            "message": "审核拒绝",
            "request_id": request_id
        }


# ===== 通知管理 =====

@router.get("/notifications")
async def get_admin_notifications(
    unread_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """获取管理员通知（预留）"""
    # 实际应该从数据库或 Redis 查询
    return {"notifications": []}


@router.post("/broadcast")
async def broadcast_message(
    message: dict,
    db: AsyncSession = Depends(get_db)
):
    """广播系统消息给所有用户（预留）"""
    return {"message": "广播已发送"}
