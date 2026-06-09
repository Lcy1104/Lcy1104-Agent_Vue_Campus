"""Chat session schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionSchema(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class SessionCreate(SessionSchema):
    title: str | None = Field(None, max_length=255)
    model_id: str | None = None
    strategy: str | None = None


class SessionUpdate(SessionSchema):
    title: str | None = Field(None, min_length=1, max_length=255)
    model_id: str | None = None
    strategy: str | None = None


class SessionResponse(SessionSchema):
    id: str
    title: str
    model_id: str | None = None
    strategy: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None


class MessageListResponse(BaseModel):
    total: int
    messages: list[MessageResponse]
