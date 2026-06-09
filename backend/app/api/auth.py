"""
API Routes - Auth
Based on need.md: backend/app/api/auth.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.utils.captcha import captcha_service
from app.services.audit_service import record_audit_event
from app.services.user_service import auth_service
from app.schemas.auth import LoginRequest, TokenResponse, CaptchaResponse, ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, ProfileResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _profile_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
        "registration_status": user.registration_status,
        "force_password_change": user.force_password_change,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
    }


@router.get("/me", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前登录用户个人资料"""
    return _profile_response(current_user)


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """获取验证码"""
    captcha_id, image_data = captcha_service.create()
    return CaptchaResponse(captcha_id=captcha_id, image_data=image_data)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    ip_address = request.client.host if request.client else None
    
    success, message, user_data = await auth_service.login(
        db=db,
        username=login_data.username,
        password=login_data.password,
        captcha_id=login_data.captcha_id,
        captcha_code=login_data.captcha_code,
        ip_address=ip_address
    )
    
    if not success:
        await record_audit_event(
            db,
            "login_failed",
            resource_type="user",
            resource_id=login_data.username,
            details={"reason": message},
            ip_address=ip_address,
        )
        if user_data and user_data.get("require_password_change"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=user_data
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )

    await record_audit_event(
        db,
        "login",
        user_id=user_data.get("user", {}).get("id"),
        resource_type="user",
        resource_id=user_data.get("user", {}).get("id"),
        details={"username": login_data.username},
        ip_address=ip_address,
    )
    return TokenResponse(**user_data)


@router.post("/register")
async def register(
    request: Request,
    register_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    success, message, user_data = await auth_service.register(
        db=db,
        username=register_data.username,
        password=register_data.password,
        captcha_id=register_data.captcha_id,
        captcha_code=register_data.captcha_code
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    await record_audit_event(
        db,
        "user_register",
        resource_type="user",
        resource_id=user_data.get("id") if isinstance(user_data, dict) else None,
        details={"username": register_data.username},
        ip_address=request.client.host if request.client else None,
    )
    return {"message": message, "user": user_data}


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    success, message = await auth_service.change_password(
        db=db,
        user_id=password_data.user_id,
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    await record_audit_event(
        db,
        "password_change",
        user_id=password_data.user_id,
        resource_type="user",
        resource_id=password_data.user_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": message}


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    忘记密码申请
    用户提交用户名，如果存在则创建审核请求，通知管理员
    """
    from app.services.user_service import process_forgot_password_request
    
    # 获取客户端真实IP地址
    # 优先级：X-Forwarded-For > X-Real-IP > client.host > unknown
    ip_address = None
    
    headers = {k.lower(): v for k, v in request.headers.items()}
    
    # 检查 X-Forwarded-For 头（Nginx反向代理）- 使用小写
    forwarded_for = headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    
    # 如果没有，检查 X-Real-IP
    if not ip_address:
        ip_address = headers.get("x-real-ip")
    
    # 如果还没有，直接使用 client.host
    if not ip_address and request.client:
        ip_address = request.client.host
    
    # 如果都没有，标记为 unknown
    if not ip_address:
        ip_address = "unknown"
    
    result = await process_forgot_password_request(
        db=db,
        username=forgot_data.username,
        captcha_id=forgot_data.captcha_id,
        captcha_code=forgot_data.captcha_code,
        ip_address=ip_address
    )
    
    if not result["success"]:
        if result.get("user_not_found"):
            # 直接提示用户不存在
            return {
                "message": "账户不存在，请重新输入"
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    await record_audit_event(
        db,
        "password_reset_request",
        resource_type="password_reset",
        resource_id=result.get("request_id"),
        details={"username": forgot_data.username},
        ip_address=ip_address,
    )
    return {
        "message": result.get("message", "密码重置申请已提交，请等待管理员审核"),
        "request_id": result.get("request_id"),
        "can_reset": result.get("can_reset", False)
    }


@router.post("/reset-password")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户通过忘记密码流程设置新密码
    需要：用户名、新密码、确认密码、验证码
    """
    from app.services.user_service import process_reset_password
    
    ip_address = request.client.host if request.client else None
    
    result = await process_reset_password(
        db=db,
        username=data.username,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
        captcha_id=data.captcha_id,
        captcha_code=data.captcha_code,
        ip_address=ip_address
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    await record_audit_event(
        db,
        "password_reset_complete",
        resource_type="user",
        resource_id=data.username,
        details={"username": data.username},
        ip_address=ip_address,
    )
    return {"message": result["message"]}



class CheckResetStatusRequest(BaseModel):
    """检查重置密码状态请求"""
    username: str = Field(..., min_length=3, max_length=100)


@router.post("/check-reset-status")
async def check_reset_status(
    data: CheckResetStatusRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    检查用户是否有已通过的密码重置申请
    """
    from app.services.user_service import check_reset_status as check_status
    
    result = await check_status(
        db=db,
        username=data.username
    )
    
    return result
