-- =====================================================
-- Agent Campus 数据库初始化脚本
-- 数据库名: agent_cam
-- 基于 db.md 完整定义，含最终完善要点
-- =====================================================

-- 1. 创建数据库（请在 psql 或 pgAdmin 中执行）
-- CREATE DATABASE agent_cam WITH ENCODING = 'UTF8';
-- \c agent_cam;

-- 2. 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. 设置时区（可选，根据需要调整）
SET TIME ZONE 'Asia/Shanghai';

-- =====================================================
-- 表 1: 用户表 users
-- 安全说明：password_hash 使用 Argon2id
--          reset_token 存储 SHA-256 哈希值
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    reset_token VARCHAR(255),  -- 存储 SHA-256(token) 哈希值
    reset_token_expires TIMESTAMPTZ
);

COMMENT ON TABLE users IS '系统用户表';
COMMENT ON COLUMN users.password_hash IS 'Argon2id 哈希值';
COMMENT ON COLUMN users.reset_token IS 'SHA-256(token) 哈希值，非明文';

-- =====================================================
-- 表 2: 登录日志 login_logs
-- 用途：安全审计和暴力破解检测
-- =====================================================
CREATE TABLE login_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    login_time TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    fail_reason VARCHAR(100)  -- invalid_password, captcha_error 等
);

COMMENT ON TABLE login_logs IS '登录日志，用于安全审计';

-- =====================================================
-- 表 3: 会话表 sessions
-- 注意：包含 model_id 关联模型注册表
-- =====================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT '新对话',
    model_id UUID,  -- 该会话当前使用的模型，可空
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE sessions IS '历史会话主表';
COMMENT ON COLUMN sessions.model_id IS '关联 model_registry.id，记录当前使用的模型';

-- =====================================================
-- 表 4: 消息表 messages
-- 注意：tool_calls 记录工具调用，metadata 可存引用/附件
-- =====================================================
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,  -- 工具调用详情
    metadata JSONB,    -- 可存：模型名称、token消耗、知识库引用、附件路径等
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE messages IS '会话中的具体消息';
COMMENT ON COLUMN messages.metadata IS '附加信息：模型名称、token消耗、知识库引用、语音/图片附件路径等';

-- =====================================================
-- 表 5: 知识库文档表 documents
-- 注意：is_public 控制普通用户是否可检索
--       status 追踪处理进度
-- =====================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),  -- pdf, docx, txt, url
    file_path TEXT,         -- 服务器存储路径或原 URL
    file_size BIGINT,       -- 字节数
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    is_public BOOLEAN DEFAULT TRUE,  -- 普通用户可检索
    status VARCHAR(20) DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'error')),
    error_message TEXT,     -- 处理失败原因
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE documents IS '文档主表，知识库管理';
COMMENT ON COLUMN documents.is_public IS '是否公共库（普通用户可检索）';

-- =====================================================
-- 表 6: 文档块表 doc_chunks（pgvector 向量存储）
-- 最终完善要点：embedding 使用 vector（不指定维度）
--               pgvector 0.5+ 支持动态维度
-- =====================================================
CREATE TABLE doc_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    chunk_text TEXT NOT NULL,
    embedding vector,  -- 不指定维度，pgvector 0.5+ 支持动态维度
    metadata JSONB,    -- 页码、章节等附加信息
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE doc_chunks IS '文档分块（含向量）';
COMMENT ON COLUMN doc_chunks.embedding IS '向量，不指定维度以兼容多模型（768/1024/1536等）';

-- =====================================================
-- 表 7: 模型后端表 model_backends
-- 注意：api_key_encrypted 使用 AES-256-GCM 加密
-- =====================================================
CREATE TABLE model_backends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,  -- 如 "本地Ollama", "阿里百炼"
    type VARCHAR(50) NOT NULL CHECK (type IN ('ollama', 'vllm', 'openai', 'anthropic', 'custom')),
    base_url VARCHAR(500) NOT NULL,     -- API 基础地址
    api_key_encrypted TEXT,             -- AES-256-GCM 加密，密钥独立存放
    health_check_url VARCHAR(500),      -- 健康检查端点
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE model_backends IS '推理后端节点配置';
COMMENT ON COLUMN model_backends.api_key_encrypted IS 'AES-256-GCM 加密，密钥需存储于环境变量';

-- =====================================================
-- 表 8: 模型注册表 model_registry
-- 注意：capabilities 标明 text/vision/audio/tool_calling 能力
-- =====================================================
CREATE TABLE model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backend_id UUID NOT NULL REFERENCES model_backends(id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL,   -- 如 "qwen2.5:7b", "gpt-4"
    display_name VARCHAR(200),          -- 展示名
    capabilities JSONB,                 -- 能力标签：text, vision, audio, tool_calling
    default_params JSONB,                 -- 默认参数：temperature, max_tokens 等
    is_multimodal BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,   -- 是否全局默认文本模型
    is_visible BOOLEAN DEFAULT TRUE,    -- 是否对普通用户可见
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE model_registry IS '注册的模型列表';
COMMENT ON COLUMN model_registry.capabilities IS '能力标签：["text", "vision", "audio", "tool_calling"]';

-- 添加外键约束（sessions.model_id -> model_registry.id）
ALTER TABLE sessions 
    ADD CONSTRAINT fk_sessions_model 
    FOREIGN KEY (model_id) REFERENCES model_registry(id) ON DELETE SET NULL;

-- =====================================================
-- 表 9: 系统配置表 system_config
-- 预置配置项：max_login_attempts, session_timeout_minutes 等
-- =====================================================
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description VARCHAR(255),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE system_config IS '全局配置项';

-- 插入预置配置项
INSERT INTO system_config (key, value, description) VALUES
    ('max_login_attempts', '5', '最大登录尝试次数'),
    ('session_timeout_minutes', '30', '会话超时时间（分钟）'),
    ('default_embed_model', 'text2vec-base-chinese', '默认嵌入模型'),
    ('rate_limit_per_minute', '60', '每分钟请求速率限制'),
    ('password_min_length', '8', '密码最小长度'),
    ('captcha_enabled', 'true', '是否启用验证码'),
    ('max_file_size_mb', '50', '最大上传文件大小（MB）'),
    ('max_chunk_size', '1000', '文档分块最大字符数'),
    ('chunk_overlap', '200', '文档分块重叠字符数');

-- =====================================================
-- 表 10: 审计日志表 audit_logs
-- 用途：记录所有敏感操作，满足审计要求
-- =====================================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,          -- login, logout, create_user, delete_doc 等
    resource_type VARCHAR(50),            -- user, document, model
    resource_id VARCHAR(100),             -- 资源 ID
    details JSONB,                        -- 操作详情
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE audit_logs IS '操作审计记录，满足学校审计要求';

-- =====================================================
-- 索引创建（性能优化）
-- =====================================================

-- users 表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

-- login_logs 表索引
CREATE INDEX idx_login_logs_user_id ON login_logs(user_id);
CREATE INDEX idx_login_logs_time ON login_logs(login_time DESC);
CREATE INDEX idx_login_logs_ip ON login_logs(ip_address);
CREATE INDEX idx_login_logs_success ON login_logs(success);

-- sessions 表索引（最终完善要点：加速历史会话列表查询）
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_user_time ON sessions(user_id, updated_at DESC);
CREATE INDEX idx_sessions_archived ON sessions(is_archived);

-- messages 表索引（最终完善要点：按时间加载对话历史）
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_session_time ON messages(session_id, created_at);
CREATE INDEX idx_messages_role ON messages(role);

-- documents 表索引
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_public ON documents(is_public);
CREATE INDEX idx_documents_created ON documents(created_at DESC);

-- doc_chunks 表索引（向量索引 + 外键索引）
CREATE INDEX idx_doc_chunks_document ON doc_chunks(document_id);
-- 向量索引：使用 hnsw（推荐）或 ivfflat
CREATE INDEX idx_doc_chunks_embedding ON doc_chunks USING hnsw (embedding vector_cosine_ops);
-- 备选：如果使用 ivfflat
-- CREATE INDEX idx_doc_chunks_embedding ON doc_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- model_backends 表索引
CREATE INDEX idx_model_backends_type ON model_backends(type);
CREATE INDEX idx_model_backends_enabled ON model_backends(is_enabled);

-- model_registry 表索引
CREATE INDEX idx_model_registry_backend ON model_registry(backend_id);
CREATE INDEX idx_model_registry_default ON model_registry(is_default) WHERE is_default = TRUE;
CREATE INDEX idx_model_registry_visible ON model_registry(is_visible);

-- audit_logs 表索引
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_time ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- =====================================================
-- 函数与触发器
-- =====================================================

-- 自动更新 updated_at 字段的函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要自动更新 updated_at 的表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 权限设置建议（可选，生产环境使用）
-- =====================================================

-- 创建应用专用用户（示例，请修改密码）
-- CREATE USER app_agent_cam WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE agent_cam TO app_agent_cam;
-- GRANT USAGE ON SCHEMA public TO app_agent_cam;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_agent_cam;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_agent_cam;

-- 创建只读用户（用于报表查询）
-- CREATE USER readonly_agent_cam WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE agent_cam TO readonly_agent_cam;
-- GRANT USAGE ON SCHEMA public TO readonly_agent_cam;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_agent_cam;

-- =====================================================
-- 验证脚本
-- =====================================================

-- 查看所有表
-- \dt

-- 查看表结构（示例）
-- \d users

-- 查看索引
-- \di

-- 查看扩展
-- \dx

-- 统计记录数
-- SELECT 
--     schemaname,
--     tablename,
--     n_tup_ins - n_tup_del as row_count
-- FROM pg_stat_user_tables 
-- WHERE schemaname = 'public'
-- ORDER BY tablename;

-- =====================================================
-- 初始化完成提示
-- =====================================================

-- 插入默认管理员用户（密码需要在应用层用 Argon2 哈希后更新）
-- INSERT INTO users (username, password_hash, role, status)
-- VALUES ('admin', 'placeholder_hash', 'admin', 'active');

-- 插入示例模型后端（Ollama 本地）
-- INSERT INTO model_backends (name, type, base_url, is_enabled)
-- VALUES ('本地Ollama', 'ollama', 'http://localhost:11434', true);

-- 插入示例模型
-- INSERT INTO model_registry (backend_id, model_name, display_name, is_default, is_visible)
-- SELECT id, 'qwen2.5:7b', '通义千问 2.5 (7B)', true, true
-- FROM model_backends WHERE name = '本地Ollama';

-- =====================================================
-- 脚本结束
-- 请根据实际需求调整上述配置
-- =====================================================

-- 输出成功信息
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Agent Campus 数据库初始化完成！';
    RAISE NOTICE '数据库名: agent_cam';
    RAISE NOTICE '========================================';
    RAISE NOTICE '已创建表:';
    RAISE NOTICE '  - users (用户表)';
    RAISE NOTICE '  - login_logs (登录日志)';
    RAISE NOTICE '  - sessions (会话表)';
    RAISE NOTICE '  - messages (消息表)';
    RAISE NOTICE '  - documents (文档表)';
    RAISE NOTICE '  - doc_chunks (文档块表，含向量)';
    RAISE NOTICE '  - model_backends (模型后端表)';
    RAISE NOTICE '  - model_registry (模型注册表)';
    RAISE NOTICE '  - system_config (系统配置表)';
    RAISE NOTICE '  - audit_logs (审计日志表)';
    RAISE NOTICE '========================================';
    RAISE NOTICE '重要提示:';
    RAISE NOTICE '  1. pgvector 扩展已启用';
    RAISE NOTICE '  2. doc_chunks.embedding 使用动态维度 vector 类型';
    RAISE NOTICE '  3. 向量索引使用 hnsw (推荐)';
    RAISE NOTICE '  4. 请修改默认配置值 (system_config 表)';
    RAISE NOTICE '  5. 生产环境请设置独立数据库用户和密码';
    RAISE NOTICE '========================================';
END $$;

