"""
Security Utilities
Based on need.md: backend/app/core/security.py
"""
from datetime import datetime, timedelta
import base64
import hashlib
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Argon2 password context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Get password hash (Argon2id)"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def _api_key_secret() -> bytes:
    return hashlib.sha256(settings.API_KEY_ENCRYPTION_SECRET.encode("utf-8")).digest()


def encrypt_api_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    nonce = os.urandom(12)
    aesgcm = AESGCM(_api_key_secret())
    encrypted = aesgcm.encrypt(nonce, api_key.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")


def decrypt_api_key(encrypted_api_key: Optional[str]) -> Optional[str]:
    if not encrypted_api_key:
        return None
    raw = base64.urlsafe_b64decode(encrypted_api_key.encode("ascii"))
    nonce, encrypted = raw[:12], raw[12:]
    aesgcm = AESGCM(_api_key_secret())
    return aesgcm.decrypt(nonce, encrypted, None).decode("utf-8")
