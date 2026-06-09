"""Database audit log helpers."""
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def ensure_audit_log_schema(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(50) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(100),
            details JSONB,
            ip_address INET NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, action)"))
    await db.commit()


async def write_audit_log(
    db: AsyncSession,
    action: str,
    user_id=None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action[:50],
            resource_type=resource_type[:50] if resource_type else None,
            resource_id=str(resource_id)[:100] if resource_id else None,
            details=details or {},
            ip_address=ip_address or "0.0.0.0",
        )
    )
    await db.commit()


async def record_audit_event(
    db: AsyncSession,
    action: str,
    user_id=None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    try:
        await write_audit_log(db, action, user_id, resource_type, resource_id, details, ip_address)
    except Exception:
        await db.rollback()
