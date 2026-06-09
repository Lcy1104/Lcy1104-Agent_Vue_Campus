"""
Model management schemas.
Based on need.md: backend/app/schemas/models.py
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelBackendBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(ollama|vllm|openai|anthropic|custom)$")
    base_url: str = Field(..., min_length=1, max_length=500)
    api_key: Optional[str] = None
    is_enabled: bool = True


class ModelBackendCreate(ModelBackendBase):
    pass


class ModelBackendUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, pattern="^(ollama|vllm|openai|anthropic|custom)$")
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = None
    is_enabled: Optional[bool] = None


class ModelBackendResponse(BaseModel):
    id: str
    name: str
    type: str
    base_url: str
    has_api_key: bool
    is_enabled: bool
    created_at: Optional[datetime]


class ModelRegistryBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    backend_id: str
    model_name: str = Field(..., min_length=1, max_length=200)
    display_name: Optional[str] = Field(None, max_length=200)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    default_params: Optional[dict[str, Any]] = None
    is_multimodal: bool = False
    is_default_text: bool = False
    is_default_embed: bool = False
    is_default_vision: bool = False
    is_visible: bool = True


class ModelRegistryCreate(ModelRegistryBase):
    pass


class ModelRegistryUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    backend_id: Optional[str] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=200)
    display_name: Optional[str] = Field(None, max_length=200)
    capabilities: Optional[dict[str, Any]] = None
    default_params: Optional[dict[str, Any]] = None
    is_multimodal: Optional[bool] = None
    is_default_text: Optional[bool] = None
    is_default_embed: Optional[bool] = None
    is_default_vision: Optional[bool] = None
    is_visible: Optional[bool] = None


class ModelRegistryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    backend_id: str
    backend_name: Optional[str] = None
    backend_type: Optional[str] = None
    model_name: str
    display_name: Optional[str]
    capabilities: dict[str, Any]
    default_params: Optional[dict[str, Any]]
    is_multimodal: bool
    is_default_text: bool
    is_default_embed: bool
    is_default_vision: bool
    is_visible: bool
    created_at: Optional[datetime]


class BackendStatusResponse(BaseModel):
    backend_id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    ok: bool
    message: str
    latency_ms: Optional[int] = None
    quota_warning: bool = False
    quota_message: Optional[str] = None


class OllamaDiscoveredModel(BaseModel):
    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None
    digest: Optional[str] = None
    exists: bool = False


class OllamaScanPreviewResponse(BaseModel):
    backend_id: str
    found: int
    models: list[OllamaDiscoveredModel]


class OllamaImportRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_names: list[str] = Field(default_factory=list)


class OllamaScanResponse(BaseModel):
    backend_id: str
    found: int
    imported: int
    models: list[ModelRegistryResponse]
