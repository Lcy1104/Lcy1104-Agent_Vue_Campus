"""System configuration API."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin_user
from app.database import get_db
from app.models import User
from app.schemas.system import SystemConfigBatchUpdate, SystemConfigResponse, SystemConfigUpdate
from app.services import system_service
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/admin/system", tags=["系统配置"], dependencies=[Depends(require_admin_user)])


@router.get("/configs", response_model=list[SystemConfigResponse])
async def list_configs(db: AsyncSession = Depends(get_db)):
    return await system_service.list_configs(db)


@router.put("/configs/{key}", response_model=SystemConfigResponse)
async def update_config(key: str, payload: SystemConfigUpdate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin_user)):
    try:
        response = await system_service.update_config(db, key, payload.value)
        await record_audit_event(
            db,
            "system_config_update",
            current_user.id,
            "system_config",
            key,
            {"key": key},
            request.client.host if request.client else None,
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/configs", response_model=list[SystemConfigResponse])
async def update_configs(payload: SystemConfigBatchUpdate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin_user)):
    try:
        response = await system_service.update_configs(db, payload.values)
        await record_audit_event(db, "system_config_batch_update", current_user.id, "system_config", None, {"keys": list(payload.values.keys())}, request.client.host if request.client else None)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
