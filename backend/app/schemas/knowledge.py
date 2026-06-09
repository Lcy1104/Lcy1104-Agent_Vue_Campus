"""
Knowledge base schemas.
Based on need.md: backend/app/schemas/knowledge.py
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_path: str
    collection_id: Optional[str] = None
    collection_name: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: Optional[str]
    is_public: bool
    status: str
    error_message: Optional[str]
    processing_progress: Optional[dict] = None
    created_at: Optional[datetime]


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentResponse]


class UrlIngestRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=20)
    is_public: bool = False
    collection_name: Optional[str] = Field(None, max_length=200)


class KnowledgeCollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime]


class KnowledgeCollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class KnowledgeCollectionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class KnowledgeCollectionListResponse(BaseModel):
    total: int
    collections: list[KnowledgeCollectionResponse]


class DocumentCollectionUpdate(BaseModel):
    collection_id: Optional[str] = None
    collection_name: Optional[str] = Field(None, max_length=200)


class DocumentVisibilityUpdate(BaseModel):
    is_public: bool


class DocumentTitleUpdate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    metadata: Optional[dict] = None
    created_at: Optional[datetime]


class ChunkListResponse(BaseModel):
    total: int
    chunks: list[ChunkResponse]


class ChunkUpdate(BaseModel):
    chunk_text: str = Field(..., min_length=1)


class UploadPolicyResponse(BaseModel):
    allowed_extensions: list[str]
    max_file_size_mb: int
    max_file_size_bytes: int
    max_files_per_batch: int
