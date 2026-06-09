"""System configuration schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class SystemConfigResponse(BaseModel):
    key: str
    value: str
    description: str | None = None
    category: str
    value_type: str
    options: list[str] | None = None
    updated_at: datetime | None = None


class SystemConfigUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=500)


class SystemConfigBatchUpdate(BaseModel):
    values: dict[str, str]
