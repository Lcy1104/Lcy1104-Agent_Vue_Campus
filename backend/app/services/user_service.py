"""
User Service
Based on need.md: backend/app/services/user_service.py
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User
from app.core.security import verify_password, get_password_hash, create_access_token
from app.utils.captcha import captcha_service
from datetime import datetime, timedelta
from typing import Optional, Tuple


class AuthService:
    """认证服务"""
    
    @staticmethod
    async def login(
        db: AsyncSession,
        username: str,
        password: str,
        captcha_id: str,
        captcha_code: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """用户登录"""
        # 1. 验证验证码
        captcha_valid, captcha_error = captcha_service.verify(captcha_id, captcha_code)
        print(f"[DEBUG] 验证码验证: {captcha_valid}, 错误: {captcha_error}")
        if not captcha_valid:
            return False, captcha_error, None
        
        # 2. 查询用户
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        print(f"[DEBUG] 查询用户: {username}, 找到: {user is not None}")
        
        if not user:
            return False, "用户名或密码错误", None
        
        # 3. 检查用户注册状态
        print(f"[DEBUG] 用户状态: {user.registration_status}")
        if user.registration_status == "pending_review":
            return False, "账户正在审核中，请等待管理员批准", None
        
        if user.registration_status == "disabled":
            return False, "账户已被禁用", None
        
        # 4. 验证密码（Argon2）
        pwd_valid = verify_password(password, user.password_hash)
        print(f"[DEBUG] 密码验证: {pwd_valid}")
        if not pwd_valid:
            return False, "用户名或密码错误", None
        
        # 5. 检查是否强制修改密码
        if user.force_password_change:
            return False, "首次登录需要修改密码", {
                "require_password_change": True,
                "user_id": str(user.id),
                "message": "请修改密码后继续"
            }
        
        # 6. 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await db.commit()
        
        # 7. 生成 JWT Token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role
            }
        )
        
        return True, "登录成功", {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 24 * 60 * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        }
    
    @staticmethod
    async def register(
        db: AsyncSession,
        username: str,
        password: str,
        captcha_id: str,
        captcha_code: str
    ) -> Tuple[bool, str, Optional[dict]]:
        """用户注册"""
        # 1. 验证验证码
        captcha_valid, captcha_error = captcha_service.verify(captcha_id, captcha_code)
        if not captcha_valid:
            return False, captcha_error, None
        
        # 2. 检查用户名是否已存在
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            return False, "用户名已存在", None
        
        # 3. 检查密码长度
        if len(password) < 8:
            return False, "密码长度不能少于8位", None
        
        # 4. 创建用户（默认 pending_review 状态）
        new_user = User(
            username=username,
            password_hash=get_password_hash(password),
            role="user",
            registration_status="pending_review",
            force_password_change=False
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # 5. 通知管理员有新用户注册待审核
        from app.utils.notification import notification_service
        notification = notification_service.create_registration_notification(
            new_user.username,
            str(new_user.id)
        )
        notification_service.broadcast_to_admins(notification)
        
        return True, "注册成功，请等待管理员审核", {
            "id": str(new_user.id),
            "username": new_user.username,
            "registration_status": new_user.registration_status
        }
    
    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """修改密码"""
        # 1. 查询用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return False, "用户不存在"
        
        # 2. 验证旧密码
        if not verify_password(old_password, user.password_hash):
            return False, "原密码错误"
        
        # 3. 检查新密码长度
        if len(new_password) < 8:
            return False, "密码长度不能少于8位"
        
        # 4. 更新密码并清除强制修改标记
        user.password_hash = get_password_hash(new_password)
        user.force_password_change = False
        await db.commit()
        from app.utils.notification import notification_service

        notification_service.broadcast_to_admins({
            "type": "user_password_changed",
            "title": "用户密码已修改",
            "message": f"用户 {user.username} 修改了密码",
            "data": {"user_id": str(user.id), "username": user.username},
            "priority": "low",
        })
        
        return True, "密码修改成功"


# 全局认证服务实例
auth_service = AuthService()


def is_expired(expires_at) -> bool:
    if not expires_at:
        return False
    now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
    return now > expires_at


# 忘记密码处理
async def process_forgot_password_request(
    db: AsyncSession,
    username: str,
    captcha_id: str,
    captcha_code: str,
    ip_address: Optional[str] = None
) -> dict:
    """
    处理忘记密码请求
    1. 验证验证码
    2. 查询用户
    3. 如果存在：创建重置请求，通知管理员
    4. 如果不存在：返回友善提示
    """
    from app.models import PasswordResetRequest
    from app.utils.notification import notification_service

    # 1. 验证验证码
    captcha_valid, captcha_error = captcha_service.verify(captcha_id, captcha_code)
    if not captcha_valid:
        return {"success": False, "message": captcha_error}

    # 2. 查询用户
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        # 返回用户不存在标志
        return {
            "success": False,
            "user_not_found": True,
            "message": "账户不存在，请重新输入"
        }

    # 3. 如果已有通过且未完成的申请，本次忘记密码校验通过后允许进入设置新密码
    approved_result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "approved"
        ).order_by(PasswordResetRequest.reviewed_at.desc())
    )
    approved_request = approved_result.scalar_one_or_none()
    if approved_request:
        if is_expired(approved_request.expires_at):
            approved_request.status = "expired"
            await db.commit()
            return {"success": False, "message": "密码重置申请已过期，请重新提交申请"}

        return {
            "success": True,
            "can_reset": True,
            "message": "密码重置申请已通过，请设置新密码",
            "request_id": str(approved_request.id)
        }

    # 4. 检查是否已有待审核请求
    existing_result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "pending"
        )
    )
    if existing_result.scalar_one_or_none():
        return {
            "success": False,
            "message": "您已有一个待审核的密码重置申请，请勿重复提交"
        }

    # 5. 创建重置请求
    reset_request = PasswordResetRequest(
        user_id=user.id,
        status="pending",
        ip_address=ip_address or "0.0.0.0"  # 如果ip_address为null，使用默认值
    )
    db.add(reset_request)
    await db.commit()
    await db.refresh(reset_request)

    # 6. 通知所有管理员
    admin_result = await db.execute(select(User.id).where(User.role == "admin"))
    admin_ids = [str(admin_id) for admin_id in admin_result.scalars().all()]
    notification = notification_service.create_password_reset_notification(
        user.username,
        str(reset_request.id)
    )
    notification_service.broadcast_to_admins(notification, admin_ids)

    return {
        "success": True,
        "can_reset": False,
        "message": "密码重置申请已提交，请等待管理员审核",
        "request_id": str(reset_request.id)
    }


async def process_reset_password(
    db: AsyncSession,
    username: str,
    new_password: str,
    confirm_password: str,
    captcha_id: str,
    captcha_code: str,
    ip_address: Optional[str] = None
) -> dict:
    """
    处理用户通过忘记密码流程设置新密码
    1. 验证验证码
    2. 查询用户
    3. 检查是否有已通过的密码重置申请
    4. 验证新密码强度
    5. 更新密码
    """
    from app.models import PasswordResetRequest
    
    # 1. 验证验证码
    captcha_valid, captcha_error = captcha_service.verify(captcha_id, captcha_code)
    if not captcha_valid:
        return {"success": False, "message": captcha_error}
    
    # 2. 查询用户
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        return {"success": False, "message": "账户不存在，请重新输入"}
    
    # 3. 检查是否有已通过的密码重置申请
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "approved"
        ).order_by(PasswordResetRequest.reviewed_at.desc())
    )
    reset_request = result.scalar_one_or_none()
    
    if not reset_request:
        return {"success": False, "message": "您的密码重置申请尚未通过审核或已过期"}
    
    # 检查是否过期（10分钟有效）
    if is_expired(reset_request.expires_at):
        return {"success": False, "message": "密码重置申请已过期，请重新提交"}
    
    # 4. 验证新密码
    if new_password != confirm_password:
        return {"success": False, "message": "两次输入的密码不一致"}
    
    if len(new_password) < 8:
        return {"success": False, "message": "密码长度不能少于8位"}
    
    # 密码强度检查
    import re
    if not re.search(r'[A-Z]', new_password):
        return {"success": False, "message": "密码需包含大写字母"}
    if not re.search(r'[a-z]', new_password):
        return {"success": False, "message": "密码需包含小写字母"}
    if not re.search(r'[0-9]', new_password):
        return {"success": False, "message": "密码需包含数字"}
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', new_password):
        return {"success": False, "message": "密码需包含特殊字符"}
    
    # 5. 更新密码
    user.password_hash = get_password_hash(new_password)
    user.force_password_change = False
    
    # 更新重置请求状态为已完成
    reset_request.status = "completed"
    
    await db.commit()
    from app.utils.notification import notification_service

    notification_service.broadcast_to_admins({
        "type": "user_password_changed",
        "title": "用户密码已重置",
        "message": f"用户 {user.username} 完成了密码重置",
        "data": {"user_id": str(user.id), "username": user.username},
        "priority": "low",
    })
    
    return {"success": True, "message": "密码重置成功，请使用新密码登录"}


async def check_reset_status(
    db: AsyncSession,
    username: str
) -> dict:
    """
    检查用户是否有已通过的密码重置申请
    """
    from app.models import PasswordResetRequest
    
    # 查询用户
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        return {"can_reset": False, "message": "账户不存在"}
    
    # 查询已通过的密码重置申请
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "approved"
        ).order_by(PasswordResetRequest.reviewed_at.desc())
    )
    reset_request = result.scalar_one_or_none()
    
    if not reset_request:
        return {"can_reset": False, "message": "您的密码重置申请尚未通过审核或已过期"}
    
    # 检查是否过期（10分钟有效）
    if is_expired(reset_request.expires_at):
        return {"can_reset": False, "message": "密码重置申请已过期，请重新提交申请"}
    
    return {"can_reset": True, "message": "可以设置新密码"}
