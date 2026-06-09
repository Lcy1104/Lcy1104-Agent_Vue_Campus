from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.tools import AgentToolCreate, AgentToolResponse, AgentToolUpdate, ToolTestResponse
from app.services import tool_service
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/tools", tags=["MCP 与外部 API 工具"])


@router.get("", response_model=list[AgentToolResponse])
async def list_tools(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await tool_service.list_available_tools(db, current_user, include_disabled=True)


@router.get("/enabled", response_model=list[AgentToolResponse])
async def list_enabled_tools(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await tool_service.list_available_tools(db, current_user, include_disabled=False)


@router.post("", response_model=AgentToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(payload: AgentToolCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    response = await tool_service.create_tool(db, current_user, payload.model_dump())
    await record_audit_event(db, "tool_create", current_user.id, "tool", response["id"], {"name": response["name"], "type": response["tool_type"]}, request.client.host if request.client else None)
    return response


@router.put("/{tool_id}", response_model=AgentToolResponse)
async def update_tool(tool_id: str, payload: AgentToolUpdate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    if not tool_service.can_manage_tool(tool, current_user):
        raise HTTPException(status_code=403, detail="只能管理自己的工具")
    data = payload.model_dump(exclude_unset=True)
    response = await tool_service.update_tool(db, tool, current_user, data)
    await record_audit_event(db, "tool_update", current_user.id, "tool", tool_id, {"fields": list(data.keys())}, request.client.host if request.client else None)
    return response


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool(tool_id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    if not tool_service.can_manage_tool(tool, current_user):
        raise HTTPException(status_code=403, detail="只能测试自己管理的工具")
    response = await tool_service.test_tool_connection(tool)
    await record_audit_event(db, "tool_test", current_user.id, "tool", tool_id, {"ok": response.get("ok")}, request.client.host if request.client else None)
    return response


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    if not tool_service.can_manage_tool(tool, current_user):
        raise HTTPException(status_code=403, detail="只能删除自己的工具")
    tool_name = tool.name
    await tool_service.delete_tool(db, tool)
    await record_audit_event(db, "tool_delete", current_user.id, "tool", tool_id, {"name": tool_name}, request.client.host if request.client else None)
    return {"message": "工具已删除"}
