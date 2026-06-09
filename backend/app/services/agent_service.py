"""Agent configuration service."""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graphs.registry import BUILTIN_AGENT_STRATEGIES, get_strategy_metadata, list_strategy_metadata
from app.models import AgentConfig, ModelRegistry


def _agent_config_response(config: AgentConfig) -> dict[str, Any]:
    metadata = get_strategy_metadata(config.strategy_name)
    return {
        "id": str(config.id),
        "strategy_name": config.strategy_name,
        "display_name": metadata["display_name"],
        "description": metadata["description"],
        "is_enabled": config.is_enabled,
        "sub_agent_models": config.sub_agent_models or {},
        "max_iterations": config.max_iterations,
        "timeout_seconds": config.timeout_seconds,
        "graph_nodes": metadata["graph_nodes"],
        "graph_edges": metadata["graph_edges"],
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


async def ensure_default_agent_configs(db: AsyncSession) -> None:
    result = await db.execute(select(AgentConfig.strategy_name))
    existing_names = set(result.scalars().all())
    for strategy_name in BUILTIN_AGENT_STRATEGIES:
        if strategy_name not in existing_names:
            db.add(AgentConfig(strategy_name=strategy_name, is_enabled=True))
    await db.commit()


async def list_configs(db: AsyncSession) -> list[dict[str, Any]]:
    await ensure_default_agent_configs(db)
    result = await db.execute(select(AgentConfig).order_by(AgentConfig.strategy_name.asc()))
    configs = sorted(
        result.scalars().all(),
        key=lambda config: list(BUILTIN_AGENT_STRATEGIES).index(config.strategy_name),
    )
    return [_agent_config_response(config) for config in configs if config.strategy_name in BUILTIN_AGENT_STRATEGIES]


async def list_strategies() -> list[dict[str, Any]]:
    return list_strategy_metadata()


async def get_config(db: AsyncSession, strategy_name: str) -> AgentConfig | None:
    if strategy_name not in BUILTIN_AGENT_STRATEGIES:
        return None
    await ensure_default_agent_configs(db)
    result = await db.execute(select(AgentConfig).where(AgentConfig.strategy_name == strategy_name))
    return result.scalar_one_or_none()


async def update_config(db: AsyncSession, config: AgentConfig, data: dict[str, Any]) -> dict[str, Any]:
    if data.get("is_enabled") is not None:
        config.is_enabled = data["is_enabled"]
    if data.get("max_iterations") is not None:
        config.max_iterations = data["max_iterations"]
    if data.get("timeout_seconds") is not None:
        config.timeout_seconds = data["timeout_seconds"]
    if data.get("sub_agent_models") is not None:
        config.sub_agent_models = await _clean_sub_agent_models(db, config.strategy_name, data["sub_agent_models"])
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    return _agent_config_response(config)


async def _clean_sub_agent_models(db: AsyncSession, strategy_name: str, sub_agent_models: dict[str, str | None]) -> dict[str, str]:
    allowed_keys = set(BUILTIN_AGENT_STRATEGIES[strategy_name]["configurable_models"])
    cleaned = {}
    for key, model_id in sub_agent_models.items():
        if key not in allowed_keys or not model_id:
            continue
        result = await db.execute(select(ModelRegistry.id).where(ModelRegistry.id == UUID(model_id)))
        if result.scalar_one_or_none() is None:
            raise ValueError(f"模型不存在：{model_id}")
        cleaned[key] = model_id
    return cleaned
