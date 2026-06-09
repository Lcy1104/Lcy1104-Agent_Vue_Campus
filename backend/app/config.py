"""
Application Configuration
Based on need.md: backend/app/config.py
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/agent_cam"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = "Password123@redis"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    API_KEY_ENCRYPTION_SECRET: str = "change-this-api-key-encryption-secret"
    RATE_LIMIT_PER_MINUTE: int = 120
    MAX_UPLOAD_SIZE_MB: int = 100
    LOCAL_MODEL_ROOT_PATH: str = r"F:\MaxKB-2.1.2\MaxKB-2.1.2\models"
    TEXT2VEC_MODEL_PATH: str = r"F:\MaxKB-2.1.2\MaxKB-2.1.2\models\text2vec-base-chinese"
    BERT_MODEL_PATH: str = r"F:\MaxKB-2.1.2\MaxKB-2.1.2\models\bert-base-chinese"
    KNOWLEDGE_CHUNK_SIZE: int = 800
    KNOWLEDGE_CHUNK_OVERLAP: int = 120
    KNOWLEDGE_CHUNK_TOKENS: int = 420
    KNOWLEDGE_CHUNK_TOKEN_OVERLAP: int = 60
    
    # Captcha
    CAPTCHA_EXPIRE_SECONDS: int = 300
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
