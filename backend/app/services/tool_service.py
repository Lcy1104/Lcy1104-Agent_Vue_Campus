from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentTool, User
from app.utils.sanitizer import sanitize_payload, sanitize_text


def _tool_response(tool: AgentTool, current_user: User, owner_name: str | None = None) -> dict[str, Any]:
    return {
        "id": str(tool.id),
        "owner_id": str(tool.owner_id),
        "owner_name": owner_name,
        "owned_by_me": tool.owner_id == current_user.id,
        "name": tool.name,
        "description": tool.description,
        "tool_type": tool.tool_type,
        "endpoint": tool.endpoint,
        "method": tool.method,
        "headers": tool.headers or {},
        "body_template": tool.body_template or {},
        "is_public": tool.is_public,
        "is_enabled": tool.is_enabled,
        "created_at": tool.created_at,
        "updated_at": tool.updated_at,
    }


async def list_available_tools(db: AsyncSession, current_user: User, include_disabled: bool = False) -> list[dict[str, Any]]:
    conditions = [or_(AgentTool.owner_id == current_user.id, AgentTool.is_public.is_(True))]
    if not include_disabled:
        conditions.append(AgentTool.is_enabled.is_(True))
    result = await db.execute(
        select(AgentTool, User.username)
        .join(User, User.id == AgentTool.owner_id)
        .where(*conditions)
        .order_by(AgentTool.is_public.desc(), AgentTool.created_at.desc())
    )
    return [_tool_response(tool, current_user, owner_name) for tool, owner_name in result.all()]


async def get_tool(db: AsyncSession, tool_id: str) -> AgentTool | None:
    result = await db.execute(select(AgentTool).where(AgentTool.id == UUID(tool_id)))
    return result.scalar_one_or_none()


def can_use_tool(tool: AgentTool, current_user: User) -> bool:
    return tool.is_enabled and (tool.is_public or tool.owner_id == current_user.id or current_user.role == "admin")


def can_manage_tool(tool: AgentTool, current_user: User) -> bool:
    return tool.owner_id == current_user.id or current_user.role == "admin"


async def create_tool(db: AsyncSession, current_user: User, data: dict[str, Any]) -> dict[str, Any]:
    tool = AgentTool(
        owner_id=current_user.id,
        name=sanitize_text(data["name"]),
        description=sanitize_text(data.get("description") or "") or None,
        tool_type=data["tool_type"],
        endpoint=data["endpoint"].strip(),
        method=data.get("method") or "POST",
        headers=sanitize_payload(data.get("headers") or {}),
        body_template=sanitize_payload(data.get("body_template") or {}),
        is_public=data.get("is_public", False),
        is_enabled=data.get("is_enabled", True),
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return _tool_response(tool, current_user, current_user.username)


async def update_tool(db: AsyncSession, tool: AgentTool, current_user: User, data: dict[str, Any]) -> dict[str, Any]:
    for field in ["name", "description", "endpoint"]:
        if field in data and data[field] is not None:
            value = data[field].strip() if field == "endpoint" else sanitize_text(data[field])
            setattr(tool, field, value or None if field == "description" else value)
    for field in ["tool_type", "method", "is_public", "is_enabled"]:
        if field in data and data[field] is not None:
            setattr(tool, field, data[field])
    for field in ["headers", "body_template"]:
        if field in data and data[field] is not None:
            setattr(tool, field, sanitize_payload(data[field]))
    await db.commit()
    await db.refresh(tool)
    return _tool_response(tool, current_user, current_user.username if tool.owner_id == current_user.id else None)


async def delete_tool(db: AsyncSession, tool: AgentTool) -> None:
    await db.delete(tool)
    await db.commit()


async def get_selected_tools(db: AsyncSession, current_user: User, tool_ids: list[str]) -> list[AgentTool]:
    if not tool_ids:
        return []
    ids = [UUID(tool_id) for tool_id in tool_ids]
    result = await db.execute(select(AgentTool).where(AgentTool.id.in_(ids)))
    tools = result.scalars().all()
    return [tool for tool in tools if can_use_tool(tool, current_user)]


async def test_tool_connection(tool: AgentTool) -> dict[str, Any]:
    if tool.tool_type == "mcp":
        return await _test_mcp_connection(tool)
    return await _test_external_api_connection(tool)


async def _test_external_api_connection(tool: AgentTool) -> dict[str, Any]:
    try:
        headers = tool.headers or {}
        body = dict(tool.body_template or {})
        body.setdefault("query", "connection_test")
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.request(
                tool.method,
                tool.endpoint,
                headers=headers,
                json=body if tool.method != "GET" else None,
                params=body if tool.method == "GET" else None,
            )
        ok = response.status_code < 400
        return {
            "ok": ok,
            "status_code": response.status_code,
            "message": "连接正常" if ok else f"服务返回 HTTP {response.status_code}",
        }
    except Exception as exc:
        return {"ok": False, "message": f"无法连接：{exc}"}


async def _test_mcp_connection(tool: AgentTool) -> dict[str, Any]:
    config = tool.body_template or {}
    transport = config.get("transport") or "sse"
    try:
        from mcp import ClientSession
        if transport == "stdio":
            from mcp.client.stdio import StdioServerParameters, stdio_client
            params = StdioServerParameters(
                command=tool.endpoint,
                args=config.get("args") or [],
                env=config.get("env"),
                cwd=config.get("cwd"),
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    return await _mcp_connection_result(session)
        if transport == "streamable_http":
            from mcp.client.streamable_http import streamablehttp_client
            async with streamablehttp_client(tool.endpoint, headers=tool.headers or {}) as (read, write, _session_id):
                async with ClientSession(read, write) as session:
                    return await _mcp_connection_result(session)
        from mcp.client.sse import sse_client
        async with sse_client(tool.endpoint, headers=tool.headers or {}) as (read, write):
            async with ClientSession(read, write) as session:
                return await _mcp_connection_result(session)
    except Exception as exc:
        return {"ok": False, "message": f"无法连接 MCP 服务：{exc}"}


async def _mcp_connection_result(session) -> dict[str, Any]:
    await session.initialize()
    tools = await session.list_tools()
    data = tools.model_dump(mode="json") if hasattr(tools, "model_dump") else {"tools": []}
    names = [item.get("name") for item in data.get("tools", []) if isinstance(item, dict) and item.get("name")]
    return {
        "ok": True,
        "message": f"连接正常，发现 {len(names)} 个工具" if names else "连接正常，但未发现可用工具",
        "available_tools": names,
    }
