"""
Model management API.
Based on need.md: backend/app/api/models_mgmt.py
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_admin_user
from app.models import User
from app.schemas.models import (
    BackendStatusResponse,
    ModelBackendCreate,
    ModelBackendResponse,
    ModelBackendUpdate,
    ModelRegistryCreate,
    ModelRegistryResponse,
    ModelRegistryUpdate,
    OllamaImportRequest,
    OllamaScanPreviewResponse,
    OllamaScanResponse,
)
from app.services import model_service
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/admin", tags=["模型管理"], dependencies=[Depends(require_admin_user)])
public_router = APIRouter(prefix="/api/models", tags=["模型"])


@public_router.get("/visible", response_model=list[ModelRegistryResponse])
async def list_visible_models(db: AsyncSession = Depends(get_db), _current_user=Depends(get_current_user)):
    return await model_service.list_visible_models(db)


@router.get("/model-backends", response_model=list[ModelBackendResponse])
async def list_model_backends(db: AsyncSession = Depends(get_db)):
    return await model_service.list_backends(db)


@router.get("/model-backends/status", response_model=list[BackendStatusResponse])
async def list_model_backend_status(db: AsyncSession = Depends(get_db)):
    return await model_service.list_backend_statuses(db)


@router.post("/model-backends", response_model=ModelBackendResponse, status_code=status.HTTP_201_CREATED)
async def create_model_backend(payload: ModelBackendCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin_user)):
    try:
        response = await model_service.create_backend(db, payload.model_dump())
        await record_audit_event(db, "model_backend_create", current_user.id, "model_backend", response["id"], {"name": response["name"], "type": response["type"]}, request.client.host if request.client else None)
        return response
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="模型后端名称已存在")


@router.put("/model-backends/{backend_id}", response_model=ModelBackendResponse)
async def update_model_backend(
    backend_id: str,
    payload: ModelBackendUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    backend = await model_service.get_backend(db, backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="模型后端不存在")
    try:
        response = await model_service.update_backend(db, backend, payload.model_dump(exclude_unset=True))
        await record_audit_event(db, "model_backend_update", current_user.id, "model_backend", backend_id, {"fields": list(payload.model_dump(exclude_unset=True).keys())}, request.client.host if request.client else None)
        return response
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="模型后端名称已存在")


@router.delete("/model-backends/{backend_id}")
async def delete_model_backend(backend_id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin_user)):
    backend = await model_service.get_backend(db, backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="模型后端不存在")
    backend_name = backend.name
    await model_service.delete_backend(db, backend)
    await record_audit_event(db, "model_backend_delete", current_user.id, "model_backend", backend_id, {"name": backend_name}, request.client.host if request.client else None)
    return {"message": "模型后端已删除"}


@router.get("/model-backends/{backend_id}/status", response_model=BackendStatusResponse)
async def test_model_backend(backend_id: str, db: AsyncSession = Depends(get_db)):
    backend = await model_service.get_backend(db, backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="模型后端不存在")
    return await model_service.test_backend_connection(backend)


@router.get("/model-backends/{backend_id}/scan", response_model=OllamaScanPreviewResponse)
async def scan_model_backend(backend_id: str, db: AsyncSession = Depends(get_db)):
    backend = await model_service.get_backend(db, backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="模型后端不存在")
    try:
        return await model_service.preview_ollama_models(db, backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"扫描 Ollama 失败：{exc}")


@router.post("/model-backends/{backend_id}/import", response_model=OllamaScanResponse)
async def import_model_backend(
    backend_id: str,
    payload: OllamaImportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    backend = await model_service.get_backend(db, backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="模型后端不存在")
    try:
        response = await model_service.import_ollama_models(db, backend, payload.model_names)
        await record_audit_event(db, "model_import", current_user.id, "model_backend", backend_id, {"model_names": payload.model_names}, request.client.host if request.client else None)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"导入 Ollama 模型失败：{exc}")


@router.get("/models", response_model=list[ModelRegistryResponse])
async def list_models(db: AsyncSession = Depends(get_db)):
    return await model_service.list_models(db)


@router.post("/models", response_model=ModelRegistryResponse, status_code=status.HTTP_201_CREATED)
async def create_model(payload: ModelRegistryCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin_user)):
    backend = await model_service.get_backend(db, payload.backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail="模型后端不存在")
    response = await model_service.create_model(db, payload.model_dump())
    await record_audit_event(db, "model_create", current_user.id, "model", response["id"], {"model_name": response["model_name"], "backend_id": payload.backend_id}, request.client.host if request.client else None)
    return response


@router.put("/models/{model_id}", response_model=ModelRegistryResponse)
async def update_model(
    model_id: str,
    payload: ModelRegistryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    model = await model_service.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("backend_id"):
        backend = await model_service.get_backend(db, data["backend_id"])
        if not backend:
            raise HTTPException(status_code=404, detail="模型后端不存在")
    response = await model_service.update_model(db, model, data)
    await record_audit_event(db, "model_update", current_user.id, "model", model_id, {"fields": list(data.keys())}, request.client.host if request.client else None)
    return response


@router.delete("/models/{model_id}")
async def delete_model(model_id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin_user)):
    model = await model_service.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    model_name = model.model_name
    await model_service.delete_model(db, model)
    await record_audit_event(db, "model_delete", current_user.id, "model", model_id, {"model_name": model_name}, request.client.host if request.client else None)
    return {"message": "模型已删除"}
