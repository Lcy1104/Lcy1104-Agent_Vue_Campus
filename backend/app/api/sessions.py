"""Chat session API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.session import MessageListResponse, SessionCreate, SessionResponse, SessionUpdate
from app.services import session_service
from app.services.audit_service import record_audit_event
from app.agent.runner import preflight_agent_reply

router = APIRouter(prefix="/api/sessions", tags=["会话"], dependencies=[Depends(get_current_user)])


class ChatPreflightRequest(BaseModel):
    strategy: str | None = None
    tool_ids: list[str] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.list_sessions(db, current_user.id, keyword)


@router.post("", response_model=SessionResponse)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response = await session_service.create_session(db, current_user.id, payload.title, payload.model_id, payload.strategy)
    await record_audit_event(db, "session_create", current_user.id, "session", response["id"], {"title": payload.title, "model_id": payload.model_id, "strategy": payload.strategy})
    return response


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    fields = payload.model_fields_set
    response = await session_service.update_session(
        db,
        session,
        payload.title if "title" in fields else session_service._UNSET,
        payload.model_id if "model_id" in fields else session_service._UNSET,
        payload.strategy if "strategy" in fields else session_service._UNSET,
    )
    await record_audit_event(db, "session_update", current_user.id, "session", session_id, {"title": payload.title, "model_id": payload.model_id, "strategy": payload.strategy})
    return response


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    await session_service.delete_session(db, session)
    await record_audit_event(db, "session_delete", current_user.id, "session", session_id)
    return {"message": "会话已删除"}


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return await session_service.list_messages(db, session)


@router.post("/{session_id}/preflight")
async def preflight_message(
    session_id: str,
    payload: ChatPreflightRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    try:
        await preflight_agent_reply(
            db,
            payload.attachments,
            str(session.model_id) if session.model_id else None,
            payload.strategy,
            payload.tool_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}
