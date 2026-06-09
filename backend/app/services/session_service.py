"""Chat session and message service."""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Session
from app.utils.sanitizer import sanitize_text


_UNSET = object()


def _session_response(session: Session) -> dict[str, Any]:
    return {
        "id": str(session.id),
        "title": session.title,
        "model_id": str(session.model_id) if session.model_id else None,
        "strategy": session.strategy,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


async def ensure_session_schema(db: AsyncSession) -> None:
    await db.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS strategy VARCHAR(100)"))
    await db.commit()


def _message_response(message: Message) -> dict[str, Any]:
    return {
        "id": message.id,
        "session_id": str(message.session_id),
        "role": message.role,
        "content": message.content,
        "tool_calls": message.tool_calls,
        "metadata": message.meta_info,
        "created_at": message.created_at,
    }


async def list_sessions(db: AsyncSession, user_id: UUID, keyword: str | None = None) -> list[dict[str, Any]]:
    await ensure_session_schema(db)
    query = select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
    if keyword:
        query = query.where(Session.title.ilike(f"%{sanitize_text(keyword)}%"))
    result = await db.execute(query)
    return [_session_response(session) for session in result.scalars().all()]


async def create_session(db: AsyncSession, user_id: UUID, title: str | None = None, model_id: str | None = None, strategy: str | None = None) -> dict[str, Any]:
    await ensure_session_schema(db)
    session = Session(
        user_id=user_id,
        title=sanitize_text(title or "新对话"),
        model_id=UUID(model_id) if model_id else None,
        strategy=sanitize_text(strategy or "single_model" if model_id else strategy or "react"),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_response(session)


async def get_session(db: AsyncSession, session_id: str, user_id: UUID) -> Session | None:
    await ensure_session_schema(db)
    result = await db.execute(select(Session).where(Session.id == UUID(session_id), Session.user_id == user_id))
    return result.scalar_one_or_none()


async def update_session(db: AsyncSession, session: Session, title: str | None | object = _UNSET, model_id: str | None | object = _UNSET, strategy: str | None | object = _UNSET) -> dict[str, Any]:
    await ensure_session_schema(db)
    if title is not _UNSET and title is not None:
        session.title = sanitize_text(title)
    if model_id is not _UNSET:
        session.model_id = UUID(model_id) if model_id else None
    if strategy is not _UNSET:
        clean_strategy = sanitize_text(strategy)
        session.strategy = clean_strategy or None
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return _session_response(session)


async def delete_session(db: AsyncSession, session: Session) -> None:
    await db.execute(delete(Message).where(Message.session_id == session.id))
    await db.delete(session)
    await db.commit()


async def list_messages(db: AsyncSession, session: Session) -> dict[str, Any]:
    result = await db.execute(select(Message).where(Message.session_id == session.id).order_by(Message.created_at.asc(), Message.id.asc()))
    messages = result.scalars().all()
    return {"total": len(messages), "messages": [_message_response(message) for message in messages]}


async def add_message(
    db: AsyncSession,
    session: Session,
    role: str,
    content: str,
    tool_calls: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = Message(
        session_id=session.id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        meta_info=metadata,
    )
    session.updated_at = datetime.utcnow()
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return _message_response(message)
