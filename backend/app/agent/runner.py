"""LangGraph-backed agent runner used by chat streaming."""
from collections.abc import AsyncIterator
from typing import Any, TypedDict
from uuid import UUID
import json

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key
from app.models import AgentConfig, ModelBackend, ModelRegistry, SystemConfig
from app.services import knowledge_service, tool_service


class ChatAgentState(TypedDict, total=False):
    db: AsyncSession
    content: str
    attachments: list[dict]
    strategy: str
    preferred_model_id: str | None
    config: AgentConfig | None
    outputs: list[dict[str, Any]]
    events: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    resolved_models: dict[str, str]
    current_user: Any
    selected_tool_ids: list[str]
    selected_collection_ids: list[str]
    history: list[dict[str, Any]]


async def stream_agent_reply(
    db: AsyncSession,
    content: str,
    attachments: list[dict] | None = None,
    preferred_model_id: str | None = None,
    selected_strategy: str | None = None,
    current_user: Any = None,
    selected_tool_ids: list[str] | None = None,
    selected_collection_ids: list[str] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict]:
    attachments = attachments or []
    if preferred_model_id and selected_strategy == "single_model":
        async for event in _stream_single_model_reply(db, content, attachments, preferred_model_id, current_user, selected_tool_ids or [], selected_collection_ids or [], history or []):
            yield event
        return

    strategy = await _resolve_strategy(db, bool(attachments), selected_strategy)
    config = await _get_agent_config(db, strategy)
    if not config:
        raise ValueError(f"Agent 策略未启用或不存在：{strategy}")
    nodes = _strategy_nodes(strategy)
    state: ChatAgentState = {
        "db": db,
        "content": content,
        "attachments": attachments,
        "strategy": strategy,
        "preferred_model_id": preferred_model_id,
        "config": config,
        "outputs": [],
        "sources": [],
        "events": [{"type": "thinking", "content": f"使用 {strategy} 策略编排 LangGraph。"}],
        "resolved_models": {},
        "current_user": current_user,
        "selected_tool_ids": selected_tool_ids or [],
        "selected_collection_ids": selected_collection_ids or [],
        "history": history or [],
    }
    await _preflight_models(state, nodes)
    for event in state.get("events", []):
        yield event
    for node in nodes:
        before = len(state.get("events", []))
        state = await _make_node(node)(state)
        for event in state.get("events", [])[before:]:
            yield event


async def _stream_single_model_reply(
    db: AsyncSession,
    content: str,
    attachments: list[dict],
    model_id: str,
    current_user: Any = None,
    selected_tool_ids: list[str] | None = None,
    selected_collection_ids: list[str] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict]:
    model = await _get_model(db, model_id)
    if not model:
        raise ValueError("选择的模型不存在，请重新选择模型")
    model_capabilities = _effective_capabilities(model)
    result = await db.execute(select(ModelBackend).where(ModelBackend.id == model.backend_id, ModelBackend.is_enabled.is_(True)))
    backend = result.scalar_one_or_none()
    if not backend:
        raise ValueError("模型后端未启用或不存在")
    if attachments and not model_capabilities.get("vision") and not model.is_multimodal:
        raise ValueError(f"当前图片输入需要视觉模型，但模型 `{model.display_name or model.model_name}` 未标记视觉能力。请更换支持视觉的模型。")
    if selected_tool_ids and not model_capabilities.get("tool_calling"):
        raise ValueError(f"当前已启用 MCP/API/Skill 工具，但模型 `{model.display_name or model.model_name}` 未标记工具调用能力。请更换支持工具调用的模型。")

    resolved_model_name = await _resolve_display_model_name(backend, model)
    yield {"type": "thinking", "content": "使用单模型直连模式，不构建 Agent 图。"}
    yield {
        "type": "model_status",
        "node": "single_model",
        "strategy": "single_model",
        "model_id": str(model.id),
        "model_name": resolved_model_name,
        "display_name": model.display_name or model.model_name,
        "registered_model_name": model.model_name,
        "ollama_base_url": _ollama_base_url(backend) if backend.backend_type == "ollama" else None,
        "backend": backend.name,
    }

    tool_context = []
    ignored_tools = []
    if current_user and selected_tool_ids:
        selected_tools = await tool_service.get_selected_tools(db, current_user, selected_tool_ids)
        for tool in selected_tools:
            tool_event = await _run_selected_tool(tool, content)
            if _tool_event_usable(tool_event):
                tool_context.append(tool_event)
            else:
                ignored_tools.append(tool_event)
            yield tool_event
    if current_user and selected_collection_ids:
        sources = await knowledge_service.search_public_chunks(db, content, limit=5, collection_ids=selected_collection_ids)
        tool_context.append({"type": "knowledge_search", "sources": sources})
        yield {"type": "sources", "sources": sources}

    prompt = _conversation_prompt(content, history or [])
    if tool_context:
        prompt = f"{prompt}\n\n已选择工具返回：\n{json.dumps(tool_context, ensure_ascii=False, default=str)}\n\n请结合工具结果回答用户。"
    elif ignored_tools:
        prompt = f"{prompt}\n\n本轮选择的外部工具均不可用或已下线，系统已忽略这些工具结果。请不要声称已经通过这些工具获取到实时数据；如果问题依赖实时数据，请简短说明对应外部服务当前不可用。"
    output = await _call_model(backend, model, prompt, attachments)
    yield {"type": "agent_step", "node": "single_model", "strategy": "single_model", "model_id": str(model.id), "model": resolved_model_name, "backend": backend.name, "content": output}
    for token in _chunk_text(output, 4):
        yield {"type": "token", "content": token}


def summarize_session_title(content: str) -> str:
    text = " ".join((content or "").strip().split())
    if not text:
        return "图片问题讨论"
    punctuation = "。！？!?\n"
    end_positions = [text.find(char) for char in punctuation if text.find(char) > 0]
    if end_positions:
        text = text[:min(end_positions)]
    return text[:24] or "新问题讨论"


async def _resolve_strategy(db: AsyncSession, has_vision_input: bool, selected_strategy: str | None = None) -> str:
    if selected_strategy in {"react", "plan_execute", "multi_agent"}:
        return selected_strategy
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == "default_agent_strategy"))
    configured = result.scalar_one_or_none()
    strategy = configured.value if configured else "react"
    if strategy not in {"react", "plan_execute", "multi_agent"}:
        strategy = "react"
    return strategy


async def _get_agent_config(db: AsyncSession, strategy: str) -> AgentConfig | None:
    result = await db.execute(select(AgentConfig).where(AgentConfig.strategy_name == strategy, AgentConfig.is_enabled.is_(True)))
    return result.scalar_one_or_none()


def _strategy_nodes(strategy: str) -> list[str]:
    if strategy == "plan_execute":
        return ["planner", "executor", "validator", "final"]
    if strategy == "multi_agent":
        return ["analyst", "executor", "validator", "final"]
    return ["agent", "tools", "final"]


def _build_graph(nodes: list[str]):
    graph = StateGraph(ChatAgentState)
    for node in nodes:
        graph.add_node(node, _make_node(node))
    graph.set_entry_point(nodes[0])
    for current_node, next_node in zip(nodes, nodes[1:]):
        graph.add_edge(current_node, next_node)
    graph.add_edge(nodes[-1], END)
    return graph.compile()


def _make_node(node_name: str):
    async def _node(state: ChatAgentState) -> ChatAgentState:
        if node_name == "tools":
            sources = []
            if state.get("selected_collection_ids"):
                sources = await knowledge_service.search_public_chunks(state["db"], state["content"], limit=5, collection_ids=state.get("selected_collection_ids"))
            selected_tools = []
            if state.get("current_user") and state.get("selected_tool_ids"):
                selected_tools = await tool_service.get_selected_tools(state["db"], state["current_user"], state.get("selected_tool_ids") or [])
            state["sources"] = sources
            if state.get("selected_collection_ids"):
                state["events"].append({
                    "type": "tool_call",
                    "name": "knowledge_search",
                    "input": {"query": state["content"], "limit": 5, "collection_ids": state.get("selected_collection_ids") or []},
                    "output": sources,
                })
            for tool in selected_tools:
                tool_result = await _run_selected_tool(tool, state["content"])
                state["events"].append(tool_result)
                if _tool_event_usable(tool_result):
                    state["outputs"].append({"node": "tools", "model": tool.name, "content": json.dumps(tool_result.get("output"), ensure_ascii=False, default=str)})
            if selected_tools and not any(_tool_event_usable(event) for event in state["events"] if event.get("type") == "tool_call" and event.get("tool_id")):
                state["outputs"].append({"node": "tools", "model": "selected_tools", "content": "本轮选择的外部工具均不可用或已下线，系统已忽略这些工具结果。不要声称已经通过这些工具获取到实时数据。"})
            if state.get("selected_collection_ids"):
                state["events"].append({"type": "sources", "sources": sources})
            observation = f"知识库{'检索完成，命中 ' + str(len(sources)) + ' 条参考来源' if state.get('selected_collection_ids') else '未启用'}。已启用 {len(selected_tools)} 个用户工具。"
            state["outputs"].append({"node": node_name, "model": "knowledge_search", "content": observation})
            state["events"].append({
                "type": "agent_step",
                "node": node_name,
                "strategy": state["strategy"],
                "model": "knowledge_search",
                "backend": "internal_tool",
                "content": observation,
            })
            state["events"].append({
                "type": "thinking",
                "node": node_name,
                "model_name": "knowledge_search",
                "backend": "internal_tool",
                "content": observation,
            })
            return state

        if node_name in {"analyst", "executor"} and not state.get("sources") and state.get("content") and state.get("selected_collection_ids"):
            sources = await knowledge_service.search_public_chunks(state["db"], state["content"], limit=5, collection_ids=state.get("selected_collection_ids") or None)
            state["sources"] = sources
            if sources:
                state["events"].append({"type": "sources", "sources": sources})
            if state.get("current_user") and state.get("selected_tool_ids"):
                selected_tools = await tool_service.get_selected_tools(state["db"], state["current_user"], state.get("selected_tool_ids") or [])
            for tool in selected_tools:
                tool_result = await _run_selected_tool(tool, state["content"])
                state["events"].append(tool_result)
                if _tool_event_usable(tool_result):
                    state["outputs"].append({"node": "tools", "model": tool.name, "content": json.dumps(tool_result.get("output"), ensure_ascii=False, default=str)})
        model, backend = await _select_model_for_state(state, node_name)
        resolved_model_name = await _resolve_display_model_name(backend, model)
        state["events"].append({
            "type": "model_status",
            "node": node_name,
            "strategy": state["strategy"],
            "model_id": str(model.id),
            "model_name": resolved_model_name,
            "registered_model_name": model.model_name,
            "ollama_base_url": _ollama_base_url(backend) if backend.backend_type == "ollama" else None,
            "backend": backend.name,
        })
        prompt = _node_prompt(node_name, state)
        output = await _call_model(backend, model, prompt, state.get("attachments") or [])
        state["outputs"].append({"node": node_name, "model": resolved_model_name, "content": output})
        state["events"].append({
            "type": "agent_step",
            "node": node_name,
            "strategy": state["strategy"],
            "model_id": str(model.id),
            "model": resolved_model_name,
            "backend": backend.name,
            "content": output,
        })
        if node_name == "final":
            for token in _chunk_text(output, 4):
                state["events"].append({"type": "token", "content": token})
        else:
            state["events"].append({
                "type": "thinking",
                "node": node_name,
                "model_name": resolved_model_name,
                "backend": backend.name,
                "content": f"{node_name} 节点完成：{output[:120]}",
            })
        return state
    return _node


def _conversation_prompt(content: str, history: list[dict[str, Any]]) -> str:
    selected = _select_relevant_history(content, history or [])
    lines = []
    for message in selected:
        role = message.get("role")
        text = (message.get("content") or "").strip()
        if role in {"user", "assistant"} and text:
            lines.append(f"{role}: {text[:800]}")
    if not lines:
        return f"用户问题：{content}"
    return "同一会话中与当前问题最相关的历史如下，请保持上下文连续；如果用户提到上文图片，以上文图片为准，不要声称无法查看图片。\n" + "\n".join(lines) + f"\n\n当前用户问题：{content}"


def _select_relevant_history(content: str, history: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    messages = [message for message in history if message.get("role") in {"user", "assistant"} and (message.get("content") or "").strip()]
    if not messages:
        return []
    query_terms = _history_terms(content)
    scored = []
    total = len(messages)
    for index, message in enumerate(messages):
        text = message.get("content") or ""
        terms = _history_terms(text)
        overlap = len(query_terms & terms)
        recency = (index + 1) / max(total, 1)
        score = overlap * 10 + recency
        if message.get("role") == "user":
            score += 0.5
        scored.append((score, index, message))
    recent_pair_start = max(total - 2, 0)
    selected_indexes = {index for index in range(recent_pair_start, total)}
    for score, index, _message in sorted(scored, key=lambda item: item[0], reverse=True):
        if score <= 0 and len(selected_indexes) >= 2:
            continue
        selected_indexes.add(index)
        if len(selected_indexes) >= limit:
            break
    return [messages[index] for index in sorted(selected_indexes)]


def _history_terms(text: str) -> set[str]:
    normalized = "".join(char.lower() if char.isalnum() or "\u4e00" <= char <= "\u9fff" else " " for char in (text or ""))
    terms = {part for part in normalized.split() if len(part) >= 2}
    chinese = [char for char in normalized if "\u4e00" <= char <= "\u9fff"]
    terms.update("".join(chinese[index:index + 2]) for index in range(max(len(chinese) - 1, 0)))
    return terms


def _tool_event_usable(event: dict[str, Any]) -> bool:
    output = event.get("output") or {}
    if isinstance(output, dict):
        if output.get("ignored"):
            return False
        if output.get("status_code") == 410:
            return False
        error = str(output.get("error") or "")
        if "410" in error and "gone" in error.lower():
            return False
    return True


async def _preflight_models(state: ChatAgentState, nodes: list[str]) -> None:
    checked: set[str] = set()
    for node in nodes:
        if node == "tools":
            continue
        lookup_node = _model_lookup_node(state["strategy"], node)
        if lookup_node in checked:
            continue
        checked.add(lookup_node)
        model, _backend = await _select_model_for_state(state, node)
        capabilities = _effective_capabilities(model)
        if state.get("attachments") and not capabilities.get("vision") and not model.is_multimodal:
            raise ValueError(
                f"当前图片输入需要视觉模型，但模型 `{model.display_name or model.model_name}` 未标记视觉能力。"
                "请更换支持视觉的模型，或在模型管理中重新扫描/保存模型能力。"
            )
        if state.get("selected_tool_ids") and node in {"agent", "planner", "analyst", "executor"} and not capabilities.get("tool_calling"):
            raise ValueError(
                f"当前已启用 MCP/API/Skill 工具，但模型 `{model.display_name or model.model_name}` 未标记工具调用能力。"
                "请更换支持工具调用的模型，或关闭本轮工具。"
            )


async def preflight_agent_reply(
    db: AsyncSession,
    attachments: list[dict] | None = None,
    preferred_model_id: str | None = None,
    selected_strategy: str | None = None,
    selected_tool_ids: list[str] | None = None,
) -> None:
    attachments = attachments or []
    if preferred_model_id and selected_strategy == "single_model":
        model = await _get_model(db, preferred_model_id)
        if not model:
            raise ValueError("选择的模型不存在，请重新选择模型")
        capabilities = _effective_capabilities(model)
        if attachments and not capabilities.get("vision") and not model.is_multimodal:
            raise ValueError(f"当前图片输入需要视觉模型，但模型 `{model.display_name or model.model_name}` 未标记视觉能力。请更换支持视觉的模型。")
        if selected_tool_ids and not capabilities.get("tool_calling"):
            raise ValueError(f"当前已启用 MCP/API/Skill 工具，但模型 `{model.display_name or model.model_name}` 未标记工具调用能力。请更换支持工具调用的模型或关闭工具。")
        return

    strategy = await _resolve_strategy(db, bool(attachments), selected_strategy)
    config = await _get_agent_config(db, strategy)
    if not config:
        raise ValueError(f"Agent 策略未启用或不存在：{strategy}")
    state: ChatAgentState = {
        "db": db,
        "content": "",
        "attachments": attachments,
        "strategy": strategy,
        "preferred_model_id": preferred_model_id,
        "config": config,
        "outputs": [],
        "sources": [],
        "events": [],
        "resolved_models": {},
        "selected_tool_ids": selected_tool_ids or [],
        "selected_collection_ids": [],
    }
    await _preflight_models(state, _strategy_nodes(strategy))


async def _run_selected_tool(tool, query: str) -> dict[str, Any]:
    base_event = {
        "type": "tool_call",
        "name": tool.name,
        "tool_id": str(tool.id),
        "tool_type": tool.tool_type,
        "input": {"query": query, "endpoint": tool.endpoint, "method": tool.method},
    }
    if tool.tool_type == "mcp":
        return {**base_event, "output": await _run_mcp_tool(tool, query)}

    try:
        import httpx
        headers = tool.headers or {}
        body = dict(tool.body_template or {})
        body.setdefault("query", query)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(tool.method, tool.endpoint, headers=headers, json=body if tool.method != "GET" else None, params=body if tool.method == "GET" else None)
        if response.status_code == 410:
            return {**base_event, "output": {"ignored": True, "status_code": 410, "reason": "外部工具服务已下线或停止服务，本轮忽略该工具结果。"}}
        output = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text[:2000]
        return {**base_event, "output": {"status_code": response.status_code, "body": output}}
    except Exception as exc:
        error = str(exc)
        if "410" in error and "gone" in error.lower():
            return {**base_event, "output": {"ignored": True, "status_code": 410, "reason": "外部工具服务已下线或停止服务，本轮忽略该工具结果。"}}
        return {**base_event, "output": {"error": error}}


async def _run_mcp_tool(tool, query: str) -> dict[str, Any]:
    config = tool.body_template or {}
    transport = config.get("transport") or "sse"
    tool_name = config.get("tool_name")
    arguments = dict(config.get("arguments") or {})
    arguments.setdefault("query", query)
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
                    await session.initialize()
                    if not tool_name:
                        return await _mcp_tool_list_hint(session)
                    result = await session.call_tool(tool_name, arguments)
                    return _mcp_result(result)
        if transport == "streamable_http":
            from mcp.client.streamable_http import streamablehttp_client
            async with streamablehttp_client(tool.endpoint, headers=tool.headers or {}) as (read, write, _session_id):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    if not tool_name:
                        return await _mcp_tool_list_hint(session)
                    result = await session.call_tool(tool_name, arguments)
                    return _mcp_result(result)
        from mcp.client.sse import sse_client
        async with sse_client(tool.endpoint, headers=tool.headers or {}) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if not tool_name:
                    return await _mcp_tool_list_hint(session)
                result = await session.call_tool(tool_name, arguments)
                return _mcp_result(result)
    except Exception as exc:
        return {"error": str(exc), "transport": transport, "tool_name": tool_name}


def _mcp_result(result) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    try:
        return json.loads(json.dumps(result, default=str))
    except Exception:
        return {"result": str(result)}


async def _mcp_tool_list_hint(session) -> dict[str, Any]:
    tools = await session.list_tools()
    data = tools.model_dump(mode="json") if hasattr(tools, "model_dump") else {"tools": str(tools)}
    names = [tool.get("name") for tool in data.get("tools", []) if isinstance(tool, dict) and tool.get("name")]
    return {
        "status": "tool_name_required",
        "message": "MCP Server 已连接成功，但需要在 MCP 配置 JSON 中填写 tool_name 后才能调用。",
        "available_tools": names,
        "raw": data,
    }


async def _select_model(db: AsyncSession, config: AgentConfig, node_name: str, has_vision_input: bool) -> tuple[ModelRegistry, ModelBackend]:
    bound_model_id = (config.sub_agent_models or {}).get(node_name)
    if bound_model_id:
        model = await _get_model(db, bound_model_id)
    else:
        model = await _get_default_model(db, vision=has_vision_input and node_name in {"analyst", "agent"})
    if not model:
        raise ValueError("没有可用模型，请先在模型管理中配置默认文本/视觉模型")
    result = await db.execute(select(ModelBackend).where(ModelBackend.id == model.backend_id, ModelBackend.is_enabled.is_(True)))
    backend = result.scalar_one_or_none()
    if not backend:
        raise ValueError("模型后端未启用或不存在")
    return model, backend


async def _select_model_for_state(state: ChatAgentState, node_name: str) -> tuple[ModelRegistry, ModelBackend]:
    lookup_node = _model_lookup_node(state["strategy"], node_name)
    bound_model_id = (state["config"].sub_agent_models or {}).get(lookup_node)
    preferred_model_id = state.get("preferred_model_id")
    if bound_model_id:
        model = await _get_model(state["db"], bound_model_id)
    elif preferred_model_id:
        model = await _get_model(state["db"], preferred_model_id)
    else:
        model = await _get_default_model(state["db"], vision=bool(state.get("attachments")) and lookup_node in {"analyst", "agent"})
    if not model:
        raise ValueError("没有可用模型，请先在模型管理中配置默认文本/视觉模型")
    model_capabilities = _effective_capabilities(model)
    if bool(state.get("attachments")) and lookup_node in {"analyst", "agent"} and not model_capabilities.get("vision") and not model.is_multimodal:
        raise ValueError(
            f"当前图片输入需要视觉模型，但模型 `{model.display_name or model.model_name}` 未标记视觉能力。"
            "请在模型管理中选择支持视觉的模型，或重新扫描 Ollama 以识别模型能力。"
        )
    if state.get("selected_tool_ids") and lookup_node in {"agent", "planner", "analyst", "executor"} and not model_capabilities.get("tool_calling"):
        raise ValueError(
            f"当前已启用 MCP/API/Skill 工具，但模型 `{model.display_name or model.model_name}` 未标记工具调用能力。"
            "请在模型管理中选择支持工具调用的模型，或在 Agent 设置中把该节点绑定到支持工具调用的模型。"
        )
    result = await state["db"].execute(select(ModelBackend).where(ModelBackend.id == model.backend_id, ModelBackend.is_enabled.is_(True)))
    backend = result.scalar_one_or_none()
    if not backend:
        raise ValueError("模型后端未启用或不存在")
    return model, backend


def _model_lookup_node(strategy: str, node_name: str) -> str:
    if node_name != "final":
        return node_name
    if strategy == "plan_execute":
        return "validator"
    if strategy == "multi_agent":
        return "validator"
    return "agent"


def _effective_capabilities(model: ModelRegistry) -> dict[str, Any]:
    capabilities = {"text": True, **(model.capabilities or {})}
    if model.is_multimodal:
        capabilities["vision"] = True
    return capabilities


async def _get_model(db: AsyncSession, model_id: str) -> ModelRegistry | None:
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == UUID(model_id)))
    return result.scalar_one_or_none()


async def _get_default_model(db: AsyncSession, vision: bool = False) -> ModelRegistry | None:
    if vision:
        result = await db.execute(select(ModelRegistry).where(ModelRegistry.is_default_vision.is_(True)))
        model = result.scalar_one_or_none()
        if model:
            return model
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.is_default_text.is_(True)))
    model = result.scalar_one_or_none()
    if model:
        return model
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.is_visible.is_(True)).order_by(ModelRegistry.created_at.desc()))
    return result.scalar_one_or_none()


def _node_prompt(node_name: str, state: ChatAgentState) -> str:
    previous = "\n".join(f"{item['node']}：{item['content']}" for item in state.get("outputs", []))
    sources = "\n".join(f"[{index + 1}] {item['filename']}：{item['snippet']}" for index, item in enumerate(state.get("sources", [])))
    attachment_note = f"\n用户附带了 {len(state.get('attachments', []))} 个图片附件。" if state.get("attachments") else ""
    base = f"用户问题：{state.get('content') or '用户仅发送了附件'}{attachment_note}\n知识库检索结果：\n{sources or '无'}\n已有中间结果：\n{previous or '无'}"
    instructions = {
        "planner": "你是规划节点，请给出解决问题的简短步骤。",
        "executor": "你是执行节点，请基于规划或分析给出主要答案。",
        "validator": "你是校验节点，请检查答案并输出最终可给用户的回复。",
        "analyst": "你是分析节点，请理解用户意图和多模态上下文。",
        "agent": "你是 ReAct Agent 的思考节点，请判断需要哪些信息和工具，并给出简短行动计划，不要输出最终答案。",
        "final": "你是最终回复节点，请综合已有中间结果、工具观察和知识库来源，输出可直接给用户的最终答案。",
    }
    return f"{instructions.get(node_name, '请处理用户问题')}\n\n{base}"


async def _call_model(backend: ModelBackend, model: ModelRegistry, prompt: str, attachments: list[dict] | None = None) -> str:
    """非流式调用，用于需要完整输出的场景"""
    api_key = decrypt_api_key(backend.api_key_encrypted)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=120) as client:
        if backend.backend_type == "ollama":
            base_url = _ollama_base_url(backend)
            ollama_model_name = await _resolve_ollama_model_name(client, backend, model)
            images = _ollama_images(attachments or [])
            payload = {"model": ollama_model_name, "prompt": prompt, "stream": False}
            if images:
                payload["images"] = images
            response = await client.post(
                f"{base_url}/api/generate",
                json=payload,
            )
            if response.status_code == 404:
                response = await client.post(
                    f"{base_url}/api/chat",
                    json={"model": ollama_model_name, "messages": [{"role": "user", "content": prompt, **({"images": images} if images else {})}], "stream": False},
                )
            if response.status_code >= 400:
                raise ValueError(_ollama_error_message(response, base_url, model, ollama_model_name))
            data = response.json()
            return data.get("message", {}).get("content") or data.get("response", "")
        if backend.backend_type in {"openai", "vllm", "custom"}:
            response = await client.post(
                f"{backend.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json={"model": model.model_name, "messages": [{"role": "user", "content": prompt}], "stream": False},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        if backend.backend_type == "anthropic":
            anthropic_headers = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
            if api_key:
                anthropic_headers["x-api-key"] = api_key
            response = await client.post(
                f"{backend.base_url.rstrip('/')}/messages",
                headers=anthropic_headers,
                json={"model": model.model_name, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            return "".join(block.get("text", "") for block in response.json().get("content", []))
    raise ValueError(f"暂不支持的模型后端：{backend.backend_type}")


def _ollama_images(attachments: list[dict]) -> list[str]:
    images = []
    for item in attachments:
        value = str(item.get("preview") or item.get("data") or "")
        if not value:
            continue
        if value.startswith("data:image/") and "," in value:
            images.append(value.split(",", 1)[1])
        elif value.startswith("/9j/") or value.startswith("iVBOR") or value.startswith("R0lGOD"):
            images.append(value)
    return images


async def _resolve_display_model_name(backend: ModelBackend, model: ModelRegistry) -> str:
    if backend.backend_type != "ollama":
        return model.display_name or model.model_name
    async with httpx.AsyncClient(timeout=8) as client:
        return await _resolve_ollama_model_name(client, backend, model)


async def _resolve_ollama_model_name(client: httpx.AsyncClient, backend: ModelBackend, model: ModelRegistry) -> str:
    base_url = _ollama_base_url(backend)
    try:
        response = await client.get(f"{base_url}/api/tags")
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(f"Ollama 后端不可用：{base_url}，请确认服务已启动并且 API 地址正确") from exc

    ollama_models = response.json().get("models", [])
    model_entries: list[tuple[str, str]] = []
    name_index: dict[str, str] = {}
    digest_index: dict[str, str] = {}
    for item in ollama_models:
        names = [item.get("name"), item.get("model")]
        name = next((str(value).strip() for value in names if value and str(value).strip()), None)
        if not name:
            continue
        digest = str(item.get("digest") or "").strip()
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        aliases = {
            name,
            str(item.get("name") or "").strip(),
            str(item.get("model") or "").strip(),
            str(item.get("remote_model") or "").strip(),
            str(details.get("family") or "").strip(),
            str(details.get("parameter_size") or "").strip(),
        }
        for alias in aliases:
            if alias:
                name_index[alias] = name
        if digest:
            digest_index[digest] = name
            for length in (8, 10, 12, 16, 24, 32):
                if len(digest) >= length:
                    digest_index[digest[:length]] = name
        model_entries.append((name, digest))

    candidates = [
        str(value).strip()
        for value in (model.model_name, model.display_name)
        if value and str(value).strip()
    ]
    for candidate in candidates:
        if candidate in name_index:
            return name_index[candidate]

    for candidate in candidates:
        if candidate in digest_index:
            return digest_index[candidate]
        for digest, name in digest_index.items():
            if digest and (digest.startswith(candidate) or candidate.startswith(digest)):
                return name

    available_names = sorted({name for name, _digest in model_entries})
    preview = "、".join(available_names[:8]) or "无"
    registered = model.model_name or "空"
    display = model.display_name or "空"
    raise ValueError(
        f"Ollama 中找不到已注册模型。注册 model_name=`{registered}`，display_name=`{display}`。"
        f"请在模型管理里重新扫描并选择已安装模型。当前可用模型：{preview}"
    )


def _ollama_base_url(backend: ModelBackend) -> str:
    base_url = (backend.base_url or "").strip().rstrip("/")
    if base_url.endswith("/api"):
        base_url = base_url[:-4].rstrip("/")
    if not base_url:
        raise ValueError("Ollama 后端 API 地址为空")
    return base_url


def _chunk_text(text: str, size: int):
    for index in range(0, len(text), size):
        yield text[index:index + size]


def _ollama_error_message(response: httpx.Response, base_url: str, model: ModelRegistry, resolved_model_name: str) -> str:
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
    except ValueError:
        error = response.text
    registered = model.model_name or "空"
    display = model.display_name or "空"
    model_hint = f"注册 model_name=`{registered}`，display_name=`{display}`，实际调用 Ollama 模型=`{resolved_model_name}`"
    if response.status_code == 404 and error:
        return f"Ollama 调用失败：{error}。{model_hint}。请在模型管理中重新扫描 {base_url}，并确认默认模型或 Agent 子图绑定模型是已安装模型。"
    return f"Ollama 调用失败（HTTP {response.status_code}，{model_hint}）：{error or response.text}"
