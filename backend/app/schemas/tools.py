from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentToolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    tool_type: Literal["mcp", "external_api"]
    endpoint: str = Field(..., min_length=1)
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"
    headers: dict[str, str] | None = None
    body_template: dict[str, Any] | None = None
    is_public: bool = False
    is_enabled: bool = True


class AgentToolCreate(AgentToolBase):
    pass


class AgentToolUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    tool_type: Literal["mcp", "external_api"] | None = None
    endpoint: str | None = Field(None, min_length=1)
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None
    headers: dict[str, str] | None = None
    body_template: dict[str, Any] | None = None
    is_public: bool | None = None
    is_enabled: bool | None = None


class AgentToolResponse(AgentToolBase):
    id: str
    owner_id: str
    owner_name: str | None = None
    owned_by_me: bool = False
    created_at: Any
    updated_at: Any


class SelectedToolsPayload(BaseModel):
    tool_ids: list[str] = []


class ToolTestResponse(BaseModel):
    ok: bool
    message: str
    status_code: int | None = None
    available_tools: list[str] = []
