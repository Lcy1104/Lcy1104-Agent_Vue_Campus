"""Agent configuration API."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.core.deps import get_current_user, require_admin_user
from app.database import get_db
from app.schemas.agent import AgentConfigResponse, AgentConfigUpdate, AgentStrategyPreview
from app.services import agent_service
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/admin/agent", tags=["Agent 设置"], dependencies=[Depends(require_admin_user)])
public_router = APIRouter(prefix="/api/agent", tags=["Agent"])


@public_router.get("/strategies", response_model=list[AgentStrategyPreview])
async def list_public_strategies(db: AsyncSession = Depends(get_db), _current_user=Depends(get_current_user)):
    configs = await agent_service.list_configs(db)
    return [
        {
            "strategy_name": config["strategy_name"],
            "display_name": config["display_name"],
            "description": config["description"],
            "graph_nodes": config["graph_nodes"],
            "graph_edges": config["graph_edges"],
            "configurable_models": [],
        }
        for config in configs
        if config["is_enabled"]
    ]


@router.get("/strategies", response_model=list[AgentStrategyPreview])
async def list_strategies():
    return await agent_service.list_strategies()


@router.get("/configs", response_model=list[AgentConfigResponse])
async def list_configs(db: AsyncSession = Depends(get_db)):
    return await agent_service.list_configs(db)


@router.put("/configs/{strategy_name}", response_model=AgentConfigResponse)
async def update_config(
    strategy_name: str,
    payload: AgentConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    config = await agent_service.get_config(db, strategy_name)
    if not config:
        raise HTTPException(status_code=404, detail="Agent 策略不存在")
    try:
        data = payload.model_dump(exclude_unset=True)
        response = await agent_service.update_config(db, config, data)
        await record_audit_event(db, "agent_config_update", current_user.id, "agent_config", strategy_name, {"fields": list(data.keys())}, request.client.host if request.client else None)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
