"""System configuration service."""
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemConfig

SYSTEM_CONFIG_DEFINITIONS: dict[str, dict[str, Any]] = {
    "captcha_expire_seconds": {
        "default": "300",
        "description": "图形验证码有效期（秒）",
        "category": "安全",
        "value_type": "integer",
        "min": 60,
        "max": 1800,
    },
    "rate_limit_per_minute": {
        "default": "120",
        "description": "单 IP 每分钟 API 请求限制",
        "category": "安全",
        "value_type": "integer",
        "min": 10,
        "max": 2000,
    },
    "session_timeout_minutes": {
        "default": "30",
        "description": "登录会话有效期（分钟）",
        "category": "安全",
        "value_type": "integer",
        "min": 5,
        "max": 1440,
    },
    "max_upload_size_mb": {
        "default": "100",
        "description": "知识库单文件最大上传大小（MB）",
        "category": "知识库",
        "value_type": "integer",
        "min": 1,
        "max": 1024,
    },
    "knowledge_process_timeout_minutes": {
        "default": "15",
        "description": "知识库前端等待处理完成的超时提示阈值（分钟）",
        "category": "知识库",
        "value_type": "integer",
        "min": 1,
        "max": 180,
    },
    "default_think_mode": {
        "default": "collapsed",
        "description": "思考过程默认显示模式",
        "category": "对话",
        "value_type": "select",
        "options": ["off", "collapsed", "full"],
    },
    "default_agent_strategy": {
        "default": "react",
        "description": "默认 Agent 策略",
        "category": "Agent",
        "value_type": "select",
        "options": ["react", "plan_execute", "multi_agent"],
    },
    "external_api_enabled": {
        "default": "false",
        "description": "是否启用外部系统 Agent API 调用入口",
        "category": "集成",
        "value_type": "boolean",
    },
}


def _response(config: SystemConfig) -> dict[str, Any]:
    definition = SYSTEM_CONFIG_DEFINITIONS[config.key]
    return {
        "key": config.key,
        "value": config.value,
        "description": config.description or definition["description"],
        "category": definition["category"],
        "value_type": definition["value_type"],
        "options": definition.get("options"),
        "updated_at": config.updated_at,
    }


async def ensure_default_configs(db: AsyncSession) -> None:
    result = await db.execute(select(SystemConfig.key))
    existing_keys = set(result.scalars().all())
    for key, definition in SYSTEM_CONFIG_DEFINITIONS.items():
        if key not in existing_keys:
            db.add(SystemConfig(key=key, value=definition["default"], description=definition["description"]))
    await db.commit()


async def list_configs(db: AsyncSession) -> list[dict[str, Any]]:
    await ensure_default_configs(db)
    result = await db.execute(select(SystemConfig).where(SystemConfig.key.in_(SYSTEM_CONFIG_DEFINITIONS.keys())))
    configs = {config.key: config for config in result.scalars().all()}
    return [_response(configs[key]) for key in SYSTEM_CONFIG_DEFINITIONS if key in configs]


async def update_config(db: AsyncSession, key: str, value: str) -> dict[str, Any]:
    if key not in SYSTEM_CONFIG_DEFINITIONS:
        raise ValueError("该系统配置不允许通过管理端修改")
    value = _validate_value(key, value)
    await ensure_default_configs(db)
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one()
    config.value = value
    config.description = SYSTEM_CONFIG_DEFINITIONS[key]["description"]
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    return _response(config)


async def update_configs(db: AsyncSession, values: dict[str, str]) -> list[dict[str, Any]]:
    for key, value in values.items():
        _validate_value(key, value)
    updated = []
    for key, value in values.items():
        updated.append(await update_config(db, key, value))
    return updated


def _validate_value(key: str, value: str) -> str:
    if key not in SYSTEM_CONFIG_DEFINITIONS:
        raise ValueError(f"未知或不可修改的配置项：{key}")
    definition = SYSTEM_CONFIG_DEFINITIONS[key]
    value = str(value).strip()
    value_type = definition["value_type"]
    if value_type == "integer":
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{key} 必须是整数") from exc
        if parsed < definition["min"] or parsed > definition["max"]:
            raise ValueError(f"{key} 必须在 {definition['min']} 到 {definition['max']} 之间")
        return str(parsed)
    if value_type == "boolean":
        lowered = value.lower()
        if lowered not in {"true", "false"}:
            raise ValueError(f"{key} 必须是 true 或 false")
        return lowered
    if value_type == "select":
        options = definition.get("options", [])
        if value not in options:
            raise ValueError(f"{key} 必须是以下值之一：{', '.join(options)}")
        return value
    return value
