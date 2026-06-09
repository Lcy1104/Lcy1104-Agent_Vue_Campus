"""
SQLAlchemy ORM Models
Based on need.md final specification
Split into separate files as per need.md structure
"""
from sqlalchemy import Column, String, DateTime, Boolean, BigInteger, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from app.database import Base
import uuid
from datetime import datetime


class User(Base):
    """用户表 - users"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # admin/user
    registration_status = Column(String(20), nullable=False, default="pending_review")
    force_password_change = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class PasswordResetRequest(Base):
    """密码重置请求表 - password_reset_requests"""
    __tablename__ = "password_reset_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    requested_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(INET, nullable=False)


class Session(Base):
    """会话表 - sessions"""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, default="新对话")
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="SET NULL"), nullable=True)
    strategy = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Message(Base):
    """消息表 - messages"""
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSONB, nullable=True)
    # 使用 meta_info 作为属性名，但数据库字段名为 metadata
    meta_info = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Document(Base):
    """文档表 - documents"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(Text, nullable=False)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_collections.id", ondelete="SET NULL"), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="processing")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class KnowledgeCollection(Base):
    """知识库归档表 - knowledge_collections"""
    __tablename__ = "knowledge_collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DocChunk(Base):
    """文档块表 - doc_chunks"""
    __tablename__ = "doc_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)
    # 使用 meta_info 作为属性名，但数据库字段名为 metadata
    meta_info = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ModelBackend(Base):
    """模型后端表 - model_backends"""
    __tablename__ = "model_backends"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    backend_type = Column("type", String(50), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ModelRegistry(Base):
    """模型注册表 - model_registry"""
    __tablename__ = "model_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backend_id = Column(UUID(as_uuid=True), ForeignKey("model_backends.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=True)
    capabilities = Column(JSONB, nullable=False, default={})
    default_params = Column(JSONB, nullable=True)
    is_multimodal = Column(Boolean, nullable=False, default=False)
    is_default_text = Column(Boolean, nullable=False, default=False)
    is_default_embed = Column(Boolean, nullable=False, default=False)
    is_default_vision = Column(Boolean, nullable=False, default=False)
    is_visible = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AgentConfig(Base):
    """Agent策略配置表 - agent_configs"""
    __tablename__ = "agent_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_name = Column(String(100), unique=True, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    sub_agent_models = Column(JSONB, nullable=True)
    max_iterations = Column(Integer, nullable=False, default=5)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AgentTool(Base):
    """MCP / external API tool configuration."""
    __tablename__ = "agent_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    tool_type = Column(String(30), nullable=False)
    endpoint = Column(Text, nullable=False)
    method = Column(String(10), nullable=False, default="POST")
    headers = Column(JSONB, nullable=True)
    body_template = Column(JSONB, nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class SystemConfig(Base):
    """系统配置表 - system_config"""
    __tablename__ = "system_config"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AuditLog(Base):
    """审计日志表 - audit_logs"""
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
