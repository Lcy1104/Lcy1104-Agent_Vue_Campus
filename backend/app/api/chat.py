"""
WebSocket Endpoint for Notifications & Chat
Based on need.md: backend/app/api/chat.py
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal, get_db
from app.core.security import verify_token
from app.models import User
from app.agent.runner import stream_agent_reply, summarize_session_title
from app.services import session_service
from app.services.audit_service import record_audit_event
from app.utils.notification import notification_service
from typing import Dict, Optional
import json
import asyncio
import httpx
import time
from contextlib import suppress

router = APIRouter(prefix="/ws", tags=["WebSocket"])


def websocket_json(payload: dict) -> str:
    return json.dumps(jsonable_encoder(payload), ensure_ascii=False)

# 活跃连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        # 标记用户在线
        notification_service.set_user_online(user_id, str(id(websocket)))
        # 发送离线消息
        await self.send_offline_messages(user_id)
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # 标记用户离线
        notification_service.set_user_offline(user_id)
    
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)
    
    async def send_offline_messages(self, user_id: str):
        """发送离线期间的消息"""
        messages = notification_service.get_offline_notifications(user_id)
        for msg in messages:
            await self.send_personal_message(json.dumps(msg), user_id)


manager = ConnectionManager()


def friendly_error_message(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        url = str(exc.request.url)
        if "localhost:11434" in url:
            try:
                payload = exc.response.json()
                detail = payload.get("error") if isinstance(payload, dict) else None
            except Exception:
                detail = exc.response.text
            if exc.response.status_code == 404:
                return f"Ollama 模型调用失败：{detail or '模型或接口不存在'}。请在模型管理中重新扫描 Ollama，并确认默认文本模型或 Agent 子图绑定模型是已安装模型。"
            return f"Ollama 模型调用失败（HTTP {exc.response.status_code}）：{detail or exc.response.text}"
    message = str(exc)
    if "http://localhost:11434/api/generate" in message or "http://localhost:11434/api/chat" in message:
        return "Ollama 模型调用失败。请在模型管理中重新扫描 Ollama，并确认当前默认模型是本机已安装模型。"
    return message


@router.websocket("/notifications")
async def notification_websocket(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSocket 通知连接
    用于：
    1. 实时接收审核通知（管理员）
    2. 接收审核结果（普通用户）
    3. 上线后同步离线消息
    """
    # 从 query 参数获取 token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    
    # 验证 token
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    user_id = payload.get("sub")
    user_role = payload.get("role")
    
    await manager.connect(user_id, websocket)
    
    # 订阅 Redis 通知通道
    import redis
    pubsub = redis.Redis(
        host='localhost',
        port=6379,
        db=1,
        password='Password123@redis',
        decode_responses=True
    ).pubsub()
    pubsub.subscribe(f"notify:{user_id}")
    if user_role == "admin":
        pubsub.subscribe("notify:admins")
    
    try:
        while True:
            # 检查 Redis 消息
            message = pubsub.get_message(timeout=1)
            if message and message['type'] == 'message':
                await websocket.send_text(message['data'])
            
            # 检查 WebSocket 消息（心跳或确认）
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                # 处理心跳
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        pubsub.unsubscribe()
    except Exception as e:
        manager.disconnect(user_id)
        pubsub.unsubscribe()


@router.websocket("/knowledge")
async def knowledge_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()
    import redis
    pubsub = redis.Redis(
        host='localhost',
        port=6379,
        db=1,
        password='Password123@redis',
        decode_responses=True
    ).pubsub()
    pubsub.subscribe("knowledge:events")
    try:
        while True:
            message = pubsub.get_message(timeout=1)
            if message and message['type'] == 'message':
                await websocket.send_text(message['data'])
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        pubsub.unsubscribe()
    except Exception:
        pubsub.unsubscribe()


@router.websocket("/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket 聊天连接
    用于实时对话（预留，后续实现）
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return

    user_id = payload.get("sub")
    await websocket.accept()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await websocket.send_text(websocket_json({"type": "error", "message": "用户不存在"}))
                return
            session = await session_service.get_session(db, session_id, user.id)
            if not session:
                await websocket.send_text(websocket_json({"type": "error", "message": "会话不存在"}))
                return

            active_task: asyncio.Task | None = None

            async def safe_send(payload: dict) -> None:
                try:
                    await websocket.send_text(websocket_json(payload))
                except Exception:
                    pass

            async def run_user_message(payload: dict):
                content = (payload.get("content") or "").strip()
                attachments = payload.get("attachments") or []
                if not content and not attachments:
                    await safe_send({"type": "error", "message": "消息不能为空"})
                    return
                async with AsyncSessionLocal() as task_db:
                    task_user = await task_db.get(User, user.id)
                    task_session = await session_service.get_session(task_db, session_id, user.id)
                    if not task_user or not task_session:
                        await safe_send({"type": "error", "message": "会话或用户不存在"})
                        return

                    existing_messages = await session_service.list_messages(task_db, task_session)
                    history_messages = existing_messages.get("messages") or []
                    context_attachments = attachments or (_latest_message_attachments(history_messages) if _references_previous_image(content) else [])

                    user_message = await session_service.add_message(task_db, task_session, "user", content, metadata={"attachments": attachments})
                    await record_audit_event(task_db, "chat_message", task_user.id, "session", session_id, {"message_id": user_message["id"], "has_attachments": bool(attachments), "content_length": len(content)})
                    await safe_send({"type": "user_saved", "message": user_message})
                    await safe_send({"type": "agent_received", "message": "后端已收到消息，正在准备 Agent 执行"})

                    if task_session.title == "新对话" and existing_messages["total"] <= 1:
                        await session_service.update_session(task_db, task_session, summarize_session_title(content))
                        await safe_send({"type": "session_title", "title": task_session.title})

                    streamed = ""
                    started_at = time.perf_counter()
                    tool_calls = []
                    thinking_parts = []
                    sources = []
                    agent_steps = []
                    model_statuses = []
                    selected_strategy = payload.get("strategy")
                    selected_tool_ids = payload.get("tool_ids") or []
                    selected_collection_ids = payload.get("collection_ids") or []
                    message_started = False
                    try:
                        async for agent_event in stream_agent_reply(task_db, content, context_attachments, str(task_session.model_id) if task_session.model_id else None, selected_strategy, task_user, selected_tool_ids, selected_collection_ids, history_messages):
                            if not message_started:
                                await safe_send({"type": "message_start", "role": "assistant"})
                                message_started = True
                            if agent_event.get("type") == "token":
                                streamed += agent_event.get("content", "")
                            elif agent_event.get("type") == "thinking":
                                thinking_parts.append({"node": agent_event.get("node"), "model_name": agent_event.get("model_name"), "backend": agent_event.get("backend"), "content": agent_event.get("content", "")})
                            elif agent_event.get("type") == "model_status":
                                model_statuses.append(agent_event)
                            elif agent_event.get("type") == "tool_call":
                                tool_calls.append(agent_event)
                            elif agent_event.get("type") == "sources":
                                sources = agent_event.get("sources") or []
                            elif agent_event.get("type") == "agent_step":
                                agent_steps.append(agent_event)
                            await safe_send(agent_event)
                            if agent_event.get("type") == "token":
                                await asyncio.sleep(0.02)
                    except ValueError as exc:
                        await safe_send({"type": "error", "message": str(exc)})
                        return
                    model_label = (model_statuses[-1].get("display_name") or model_statuses[-1].get("model_name")) if model_statuses else None
                    run_label = model_label if selected_strategy == "single_model" and model_label else "Graph"
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                    assistant_message = await session_service.add_message(task_db, task_session, "assistant", streamed, tool_calls=tool_calls or None, metadata={"thinking": thinking_parts, "sources": sources, "agent_steps": agent_steps, "model_statuses": model_statuses, "model_name": model_label, "run_label": run_label, "strategy": selected_strategy, "tool_ids": selected_tool_ids, "collection_ids": selected_collection_ids, "elapsed_ms": elapsed_ms})
                    await record_audit_event(task_db, "agent_reply", task_user.id, "session", session_id, {"message_id": assistant_message["id"], "strategy": selected_strategy, "tool_count": len(tool_calls), "source_count": len(sources)})
                    await safe_send({"type": "message_done", "message": assistant_message})

            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                if payload.get("type") == "ping":
                    await websocket.send_text(websocket_json({"type": "pong"}))
                    continue
                if payload.get("type") == "cancel_message":
                    if active_task and not active_task.done():
                        active_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await active_task
                        await websocket.send_text(websocket_json({"type": "message_cancelled", "message": "本次对话已中止"}))
                    continue
                if payload.get("type") != "user_message":
                    continue
                if active_task and not active_task.done():
                    await websocket.send_text(websocket_json({"type": "error", "message": "当前对话仍在执行。你可以点击“中止”结束本次对话，或等待结果完成。"}))
                    continue
                active_task = asyncio.create_task(run_user_message(payload))
    except WebSocketDisconnect:
        if active_task and not active_task.done():
            # The task owns its DB session and will persist the result even after the client leaves.
            pass
        pass
    except Exception as exc:
        try:
            await websocket.send_text(websocket_json({"type": "error", "message": friendly_error_message(exc)}))
        except Exception:
            pass


def _latest_message_attachments(messages: list[dict]) -> list[dict]:
    for message in reversed(messages or []):
        metadata = message.get("metadata") or {}
        attachments = metadata.get("attachments") or []
        if message.get("role") == "user" and attachments:
            return attachments
    return []


def _references_previous_image(content: str) -> bool:
    lowered = (content or "").lower()
    markers = ["图", "图片", "照片", "截图", "这个", "上面", "刚才", "上一", "专业", "表格", "image", "photo", "screenshot"]
    return any(marker in lowered for marker in markers)
