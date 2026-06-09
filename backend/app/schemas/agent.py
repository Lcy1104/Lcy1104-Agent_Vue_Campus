"""Agent configuration schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentConfigResponse(BaseModel):
    id: str
    strategy_name: str
    display_name: str
    description: str
    is_enabled: bool
    sub_agent_models: Optional[dict[str, str]] = None
    max_iterations: int
    timeout_seconds: int
    graph_nodes: list[str]
    graph_edges: list[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class AgentConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    sub_agent_models: Optional[dict[str, str | None]] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=10, le=3600)


class AgentStrategyPreview(BaseModel):
    strategy_name: str
    display_name: str
    description: str
    graph_nodes: list[str]
    graph_edges: list[str]
    configurable_models: list[str]
