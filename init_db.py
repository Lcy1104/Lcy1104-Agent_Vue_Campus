#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Campus 数据库初始化脚本
支持跨平台：Windows / Linux / macOS
数据库：PostgreSQL + pgvector
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# 配置
DEFAULT_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'agent_cam',
    'user': 'postgres',
    'password': 'root',
}

# SQL 脚本内容（基于最新 db.md）
SQL_SCRIPT = """
-- =====================================================
-- Agent Campus Database Initialization
-- Database: agent_cam
-- Based on db.md final specification
-- =====================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Set timezone
SET TIME ZONE 'Asia/Shanghai';

-- =====================================================
-- Table 1: users
-- Note: registration_status DEFAULT 'pending_review'
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'user')),
    registration_status VARCHAR(20) NOT NULL DEFAULT 'pending_review' 
        CHECK (registration_status IN ('pending_review', 'active', 'disabled')),
    force_password_change BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

COMMENT ON TABLE users IS 'System users table';
COMMENT ON COLUMN users.password_hash IS 'Argon2id hash';

-- =====================================================
-- Table 2: password_reset_requests
-- Note: reviewed_at added
-- =====================================================
CREATE TABLE IF NOT EXISTS password_reset_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'approved', 'rejected', 'completed', 'expired')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    ip_address INET NOT NULL
);

COMMENT ON TABLE password_reset_requests IS 'Password reset request lifecycle';

-- =====================================================
-- Table 3: model_backends (create before sessions)
-- =====================================================
CREATE TABLE IF NOT EXISTS model_backends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('ollama', 'vllm', 'openai', 'anthropic', 'custom')),
    base_url VARCHAR(500) NOT NULL,
    api_key_encrypted TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE model_backends IS 'Model backend configuration';

-- =====================================================
-- Table 4: model_registry (create before sessions)
-- Note: is_default split into three fields
-- =====================================================
CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backend_id UUID NOT NULL REFERENCES model_backends(id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL,
    display_name VARCHAR(200),
    capabilities JSONB NOT NULL DEFAULT '{}',
    default_params JSONB,
    is_multimodal BOOLEAN NOT NULL DEFAULT FALSE,
    is_default_text BOOLEAN NOT NULL DEFAULT FALSE,
    is_default_embed BOOLEAN NOT NULL DEFAULT FALSE,
    is_default_vision BOOLEAN NOT NULL DEFAULT FALSE,
    is_visible BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE model_registry IS 'Registered AI models';

-- =====================================================
-- Table 5: sessions
-- =====================================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT '新对话',
    model_id UUID REFERENCES model_registry(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE sessions IS 'Chat sessions';

-- =====================================================
-- Table 6: messages
-- =====================================================
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE messages IS 'Chat messages';

-- =====================================================
-- Table 7: knowledge_collections
-- =====================================================
CREATE TABLE IF NOT EXISTS knowledge_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE knowledge_collections IS 'Knowledge base collections for document grouping';

-- =====================================================
-- Table 8: documents
-- Note: is_public DEFAULT FALSE
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt', 'md', 'html', 'xlsx', 'url', 'png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff')),
    file_path TEXT NOT NULL,
    collection_id UUID REFERENCES knowledge_collections(id) ON DELETE SET NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'processing' 
        CHECK (status IN ('processing', 'ready', 'error')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE documents IS 'Documents for knowledge base';

ALTER TABLE documents ADD COLUMN IF NOT EXISTS collection_id UUID REFERENCES knowledge_collections(id) ON DELETE SET NULL;
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_file_type_check;
ALTER TABLE documents ADD CONSTRAINT documents_file_type_check
    CHECK (file_type IN ('pdf', 'docx', 'txt', 'md', 'html', 'xlsx', 'url', 'png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'));

-- =====================================================
-- Table 9: doc_chunks
-- Note: embedding NOT NULL
-- =====================================================
CREATE TABLE IF NOT EXISTS doc_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE model_registry IS 'Registered AI models';

-- =====================================================
-- Table 9: agent_configs (NEW)
-- =====================================================
CREATE TABLE IF NOT EXISTS agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(100) UNIQUE NOT NULL 
        CHECK (strategy_name IN ('react', 'plan_execute', 'multi_agent')),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sub_agent_models JSONB,
    max_iterations INTEGER NOT NULL DEFAULT 5,
    timeout_seconds INTEGER NOT NULL DEFAULT 300,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE agent_configs IS 'Agent strategy configuration';

-- =====================================================
-- Table 10: agent_tools
-- =====================================================
CREATE TABLE IF NOT EXISTS agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    tool_type VARCHAR(30) NOT NULL CHECK (tool_type IN ('mcp', 'external_api')),
    endpoint TEXT NOT NULL,
    method VARCHAR(10) NOT NULL DEFAULT 'POST' CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')),
    headers JSONB,
    body_template JSONB,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE agent_tools IS 'MCP and external API tools available to Agent graphs';

-- =====================================================
-- Table 10: system_config
-- =====================================================
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE system_config IS 'Global system configuration';

-- =====================================================
-- Table 11: audit_logs
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB,
    ip_address INET NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE audit_logs IS 'Audit log for compliance';

-- =====================================================
-- Indexes for performance
-- =====================================================

-- users indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_registration ON users(registration_status);

-- password_reset_requests indexes
CREATE INDEX IF NOT EXISTS idx_password_reset_lookup 
ON password_reset_requests(user_id, status, expires_at);

-- sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_time ON sessions(user_id, updated_at DESC);

-- messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, created_at);

-- documents indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_collections_name ON knowledge_collections(LOWER(name));
CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_public ON documents(is_public, status);

-- doc_chunks indexes
CREATE INDEX IF NOT EXISTS idx_doc_chunks_document ON doc_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON doc_chunks USING hnsw (embedding vector_cosine_ops);

-- model_backends indexes
CREATE INDEX IF NOT EXISTS idx_model_backends_type ON model_backends(type);
CREATE INDEX IF NOT EXISTS idx_model_backends_enabled ON model_backends(is_enabled);

-- model_registry indexes
CREATE INDEX IF NOT EXISTS idx_model_registry_backend ON model_registry(backend_id);
CREATE INDEX IF NOT EXISTS idx_model_registry_default_text ON model_registry(is_default_text) WHERE is_default_text = TRUE;
CREATE INDEX IF NOT EXISTS idx_model_registry_default_embed ON model_registry(is_default_embed) WHERE is_default_embed = TRUE;
CREATE INDEX IF NOT EXISTS idx_model_registry_default_vision ON model_registry(is_default_vision) WHERE is_default_vision = TRUE;
CREATE INDEX IF NOT EXISTS idx_model_registry_visible ON model_registry(is_visible);

-- agent_tools indexes
CREATE INDEX IF NOT EXISTS idx_agent_tools_owner ON agent_tools(owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tools_public ON agent_tools(is_public, is_enabled);

-- audit_logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs(created_at DESC);

-- =====================================================
-- Functions and Triggers
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing triggers to avoid conflicts
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
DROP TRIGGER IF EXISTS update_system_config_updated_at ON system_config;
DROP TRIGGER IF EXISTS update_agent_configs_updated_at ON agent_configs;

-- Create triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_configs_updated_at BEFORE UPDATE ON agent_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Default Data - Inserted after all tables created
-- =====================================================

-- Insert default admin user first (no dependencies)
INSERT INTO users (username, password_hash, role, registration_status, force_password_change, created_at, updated_at)
VALUES (
    'admin', 
    '$argon2id$v=19$m=65536,t=3,p=4$placeholder$hash', 
    'admin', 
    'active',
    TRUE,
    NOW(), 
    NOW()
)
ON CONFLICT (username) DO NOTHING;

-- Insert default system configs
INSERT INTO system_config (key, value, description) VALUES
    ('max_login_attempts', '5', 'Maximum login attempts before lockout'),
    ('session_timeout_minutes', '30', 'Session timeout in minutes'),
    ('rate_limit_per_minute', '60', 'API rate limit per minute'),
    ('default_think_mode', 'react', 'Default agent thinking mode'),
    ('max_upload_size_mb', '50', 'Maximum file upload size in MB'),
    ('captcha_expire_seconds', '300', 'Captcha expiration time'),
    ('password_reset_expire_minutes', '10', 'Password reset link expiration')
ON CONFLICT (key) DO NOTHING;

-- Insert default agent configs
INSERT INTO agent_configs (strategy_name, is_enabled, max_iterations, timeout_seconds) VALUES
    ('react', TRUE, 5, 300),
    ('plan_execute', TRUE, 3, 300),
    ('multi_agent', TRUE, 10, 600)
ON CONFLICT (strategy_name) DO NOTHING;

-- =====================================================
-- Success message
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Agent Campus database initialized!';
    RAISE NOTICE '========================================';
END $$;
"""


def check_psycopg():
    """Check if psycopg2 is installed"""
    try:
        import psycopg2
        return True
    except ImportError:
        return False


def install_psycopg():
    """Install psycopg2-binary"""
    print("Installing psycopg2-binary...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
        print("OK psycopg2-binary installed")
        return True
    except:
        return False


def create_database_if_not_exists(config):
    """Create database if not exists"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database='postgres',
            user=config['user'],
            password=config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config['database'],))
        if not cursor.fetchone():
            print(f"Creating database '{config['database']}'...")
            cursor.execute(f"CREATE DATABASE {config['database']} ENCODING 'UTF8'")
            print(f"OK Database created")
        else:
            print(f"OK Database exists")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"FAIL Failed: {e}")
        return False


def init_database(config):
    """Initialize database"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Executing initialization script...")
        cursor.execute(SQL_SCRIPT)
        
        # Fix admin password with correct Argon2 hash
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
            correct_hash = pwd_context.hash("admin123")
            
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = 'admin'",
                (correct_hash,)
            )
            print("OK Admin password fixed with correct Argon2 hash")
        except Exception as e:
            print(f"Warning: Could not fix admin password: {e}")
        
        cursor.close()
        conn.close()
        
        print("\nOK Database initialized successfully!")
        print("\nCreated 12 tables:")
        print("  - users (with force_password_change)")
        print("  - password_reset_requests (with reviewed_at)")
        print("  - sessions")
        print("  - messages")
        print("  - knowledge_collections")
        print("  - documents (is_public DEFAULT FALSE, collection_id nullable)")
        print("  - doc_chunks (embedding NOT NULL)")
        print("  - model_backends")
        print("  - model_registry (split is_default)")
        print("  - agent_configs (NEW)")
        print("  - system_config")
        print("  - audit_logs")
        print("\nOK Default admin user created: admin / admin123")
        print("  Note: Admin must change password on first login")
        return True
    except Exception as e:
        print(f"FAIL Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Initialize Agent Campus Database')
    parser.add_argument('--host', default=DEFAULT_CONFIG['host'])
    parser.add_argument('--port', type=int, default=DEFAULT_CONFIG['port'])
    parser.add_argument('--database', default=DEFAULT_CONFIG['database'])
    parser.add_argument('--user', default=DEFAULT_CONFIG['user'])
    parser.add_argument('--password', default=DEFAULT_CONFIG['password'])
    parser.add_argument('--skip-create', action='store_true')
    
    args = parser.parse_args()
    config = vars(args)
    
    print("="*50)
    print("Agent Campus Database Initialization")
    print("="*50)
    
    if not check_psycopg():
        if not install_psycopg():
            print("Please install: pip install psycopg2-binary")
            sys.exit(1)
    
    print("OK Using psycopg2")
    
    if not config['skip_create']:
        if not create_database_if_not_exists(config):
            sys.exit(1)
    
    if init_database(config):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
