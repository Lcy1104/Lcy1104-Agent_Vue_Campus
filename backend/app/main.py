"""
FastAPI 主入口
Based on need.md structure
"""
import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, chat, admin, models_mgmt, knowledge, agent, system, sessions, audio, tools
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.security import verify_token
from app.database import AsyncSessionLocal
from app.services.audit_service import ensure_audit_log_schema, write_audit_log
from app.services.knowledge_service import cleanup_stale_uploads

# 创建 FastAPI 应用
app = FastAPI(
    title="Agent Campus API",
    description="Agent Campus Backend API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_mutating_requests(request: Request, call_next):
    response = await call_next(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        payload = verify_token(token) if token else None
        user_id = payload.get("sub") if payload else None
        try:
            async with AsyncSessionLocal() as db:
                await write_audit_log(
                    db,
                    action=f"{request.method} {request.url.path}"[:50],
                    user_id=user_id,
                    resource_type=request.url.path.split("/")[2] if len(request.url.path.split("/")) > 2 else "api",
                    details={"status_code": response.status_code, "path": request.url.path},
                    ip_address=request.client.host if request.client else "0.0.0.0",
                )
        except Exception:
            pass
    return response


@app.on_event("startup")
async def start_upload_cleanup_task():
    async with AsyncSessionLocal() as db:
        await ensure_audit_log_schema(db)
    cleanup_stale_uploads(max_age_seconds=3600)

    async def _cleanup_loop():
        while True:
            await asyncio.sleep(1800)
            cleanup_stale_uploads(max_age_seconds=3600)

    asyncio.create_task(_cleanup_loop())

# 注册路由
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(models_mgmt.router)
app.include_router(models_mgmt.public_router)
app.include_router(knowledge.router)
app.include_router(knowledge.admin_router)
app.include_router(agent.router)
app.include_router(agent.public_router)
app.include_router(system.router)
app.include_router(sessions.router)
app.include_router(audio.router)
app.include_router(tools.router)


@app.get("/")
async def root():
    return {"message": "Agent Campus API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
