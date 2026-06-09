"""
Model backend and registry service.
Based on need.md: backend/app/services/model_service.py
"""
from time import perf_counter
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key, encrypt_api_key
from app.models import ModelBackend, ModelRegistry
from app.utils.sanitizer import sanitize_payload, sanitize_text


def _backend_response(backend: ModelBackend) -> dict[str, Any]:
    return {
        "id": str(backend.id),
        "name": backend.name,
        "type": backend.backend_type,
        "base_url": backend.base_url,
        "has_api_key": bool(backend.api_key_encrypted),
        "is_enabled": backend.is_enabled,
        "created_at": backend.created_at,
    }


def _model_response(model: ModelRegistry, backend: ModelBackend | None = None) -> dict[str, Any]:
    capabilities = _normalize_capabilities(model.model_name, model.display_name, model.capabilities or {}, model.is_multimodal)
    return {
        "id": str(model.id),
        "backend_id": str(model.backend_id),
        "backend_name": backend.name if backend else None,
        "backend_type": backend.backend_type if backend else None,
        "model_name": model.model_name,
        "display_name": model.display_name,
        "capabilities": capabilities,
        "default_params": model.default_params,
        "is_multimodal": model.is_multimodal or capabilities.get("vision", False),
        "is_default_text": model.is_default_text,
        "is_default_embed": model.is_default_embed,
        "is_default_vision": model.is_default_vision,
        "is_visible": model.is_visible,
        "created_at": model.created_at,
    }


async def list_backends(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(select(ModelBackend).order_by(ModelBackend.created_at.desc()))
    return [_backend_response(backend) for backend in result.scalars().all()]


async def create_backend(db: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    backend = ModelBackend(
        name=sanitize_text(data["name"]),
        backend_type=data["type"],
        base_url=_normalize_backend_base_url(data["base_url"], data["type"]),
        api_key_encrypted=encrypt_api_key(data.get("api_key")),
        is_enabled=data.get("is_enabled", True),
    )
    db.add(backend)
    await db.commit()
    await db.refresh(backend)
    return _backend_response(backend)


async def get_backend(db: AsyncSession, backend_id: str) -> ModelBackend | None:
    result = await db.execute(select(ModelBackend).where(ModelBackend.id == UUID(backend_id)))
    return result.scalar_one_or_none()


async def update_backend(db: AsyncSession, backend: ModelBackend, data: dict[str, Any]) -> dict[str, Any]:
    if data.get("name") is not None:
        backend.name = sanitize_text(data["name"])
    if data.get("type") is not None:
        backend.backend_type = data["type"]
    if data.get("base_url") is not None:
        backend.base_url = _normalize_backend_base_url(data["base_url"], data.get("type") or backend.backend_type)
    if data.get("api_key") is not None:
        backend.api_key_encrypted = encrypt_api_key(data["api_key"])
    if data.get("is_enabled") is not None:
        backend.is_enabled = data["is_enabled"]
    await db.commit()
    await db.refresh(backend)
    return _backend_response(backend)


async def delete_backend(db: AsyncSession, backend: ModelBackend) -> None:
    await db.delete(backend)
    await db.commit()


async def list_backend_statuses(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(select(ModelBackend).order_by(ModelBackend.created_at.desc()))
    statuses = []
    for backend in result.scalars().all():
        statuses.append(await test_backend_connection(backend))
    return statuses


async def list_models(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ModelRegistry, ModelBackend)
        .join(ModelBackend, ModelRegistry.backend_id == ModelBackend.id)
        .order_by(ModelRegistry.created_at.desc())
    )
    rows = result.all()
    return [_model_response(model, backend) for model, backend in rows]


async def list_visible_models(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ModelRegistry, ModelBackend)
        .join(ModelBackend, ModelRegistry.backend_id == ModelBackend.id)
        .where(ModelRegistry.is_visible.is_(True), ModelBackend.is_enabled.is_(True))
        .order_by(ModelRegistry.is_default_text.desc(), ModelRegistry.created_at.desc())
    )
    rows = result.all()
    return [_model_response(model, backend) for model, backend in rows]


async def create_model(db: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    await _clear_default_flags(db, data)
    backend = await get_backend(db, data["backend_id"])
    model_name = data["model_name"]
    capabilities = sanitize_payload(data.get("capabilities") or {"text": True})
    if backend and backend.backend_type == "ollama":
        model_name = await _resolve_ollama_model_name(backend, model_name)
        capabilities = await _fetch_ollama_capabilities(backend, model_name)
    model = ModelRegistry(
        backend_id=UUID(data["backend_id"]),
        model_name=model_name,
        display_name=sanitize_text(data.get("display_name") or model_name),
        capabilities=capabilities,
        default_params=sanitize_payload(data.get("default_params")),
        is_multimodal=capabilities.get("vision", False),
        is_default_text=data.get("is_default_text", False),
        is_default_embed=data.get("is_default_embed", False),
        is_default_vision=data.get("is_default_vision", False),
        is_visible=data.get("is_visible", True),
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return _model_response(model, backend)


async def get_model(db: AsyncSession, model_id: str) -> ModelRegistry | None:
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == UUID(model_id)))
    return result.scalar_one_or_none()


async def update_model(db: AsyncSession, model: ModelRegistry, data: dict[str, Any]) -> dict[str, Any]:
    await _clear_default_flags(db, data, exclude_model_id=str(model.id))
    should_refresh_ollama_capabilities = data.get("backend_id") is not None or data.get("model_name") is not None
    if data.get("backend_id") is not None:
        model.backend_id = UUID(data["backend_id"])
    for field in [
        "model_name",
        "display_name",
        "capabilities",
        "default_params",
        "is_multimodal",
        "is_default_text",
        "is_default_embed",
        "is_default_vision",
        "is_visible",
    ]:
        if data.get(field) is not None:
            value = data[field]
            if field == "display_name":
                value = sanitize_text(value)
            elif field in {"capabilities", "default_params"}:
                value = sanitize_payload(value)
            setattr(model, field, value)
    await db.commit()
    await db.refresh(model)
    backend = await get_backend(db, str(model.backend_id))
    if should_refresh_ollama_capabilities and backend and backend.backend_type == "ollama":
        model.model_name = await _resolve_ollama_model_name(backend, model.model_name)
        model.capabilities = await _fetch_ollama_capabilities(backend, model.model_name)
        model.is_multimodal = model.capabilities.get("vision", False)
        await db.commit()
        await db.refresh(model)
    return _model_response(model, backend)


async def delete_model(db: AsyncSession, model: ModelRegistry) -> None:
    await db.delete(model)
    await db.commit()


async def test_backend_connection(backend: ModelBackend) -> dict[str, Any]:
    started = perf_counter()
    try:
        url, headers = _status_request(backend)
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url, headers=headers)
        latency_ms = int((perf_counter() - started) * 1000)
        if response.status_code >= 400:
            message = _extract_error_message(response)
            return _backend_status_response(
                backend,
                ok=False,
                message=message,
                latency_ms=latency_ms,
                quota_warning=_is_quota_error(response, message),
                quota_message=message if _is_quota_error(response, message) else None,
            )
        return {
            "backend_id": str(backend.id),
            "name": backend.name,
            "type": backend.backend_type,
            "ok": True,
            "message": "连接正常",
            "latency_ms": latency_ms,
            "quota_warning": False,
            "quota_message": None,
        }
    except Exception as exc:
        message = str(exc)
        return _backend_status_response(
            backend,
            ok=False,
            message=message,
            latency_ms=None,
            quota_warning=_is_quota_message(message),
            quota_message=message if _is_quota_message(message) else None,
        )


async def preview_ollama_models(db: AsyncSession, backend: ModelBackend) -> dict[str, Any]:
    if backend.backend_type != "ollama":
        raise ValueError("仅 Ollama 后端支持自动扫描")

    payload = await _fetch_ollama_tags(backend)
    discovered = []
    for item in payload.get("models", []):
        model_name = item.get("name")
        if not model_name:
            continue
        existing_result = await db.execute(
            select(ModelRegistry).where(
                ModelRegistry.backend_id == backend.id,
                ModelRegistry.model_name == model_name,
            )
        )
        discovered.append(
            {
                "name": model_name,
                "size": item.get("size"),
                "modified_at": item.get("modified_at"),
                "digest": item.get("digest"),
                "exists": existing_result.scalar_one_or_none() is not None,
            }
        )

    return {
        "backend_id": str(backend.id),
        "found": len(discovered),
        "models": discovered,
    }


async def import_ollama_models(
    db: AsyncSession,
    backend: ModelBackend,
    model_names: list[str],
) -> dict[str, Any]:
    if backend.backend_type != "ollama":
        raise ValueError("仅 Ollama 后端支持自动导入")
    if not model_names:
        raise ValueError("请选择至少一个要导入的模型")

    payload = await _fetch_ollama_tags(backend)
    available_names = {item.get("name") for item in payload.get("models", []) if item.get("name")}
    selected_names = [name for name in model_names if name in available_names]
    if not selected_names:
        raise ValueError("选择的模型不存在于该 Ollama 后端")

    imported = 0
    scanned_models = []
    for model_name in selected_names:
        existing_result = await db.execute(
            select(ModelRegistry).where(
                ModelRegistry.backend_id == backend.id,
                ModelRegistry.model_name == model_name,
            )
        )
        model = existing_result.scalar_one_or_none()
        capabilities = await _fetch_ollama_capabilities(backend, model_name)
        if model is None:
            model = ModelRegistry(
                backend_id=backend.id,
                model_name=model_name,
                display_name=model_name,
                capabilities=capabilities,
                default_params={"temperature": 0.7},
                is_multimodal=capabilities.get("vision", False),
                is_visible=True,
            )
            db.add(model)
            imported += 1
        else:
            model.capabilities = capabilities
            model.is_multimodal = capabilities.get("vision", False)
        scanned_models.append(model)

    await db.commit()
    for model in scanned_models:
        await db.refresh(model)

    return {
        "backend_id": str(backend.id),
        "found": len(selected_names),
        "imported": imported,
        "models": [_model_response(model, backend) for model in scanned_models],
    }


async def scan_ollama_models(db: AsyncSession, backend: ModelBackend) -> dict[str, Any]:
    preview = await preview_ollama_models(db, backend)
    names = [model["name"] for model in preview["models"] if not model["exists"]]
    return await import_ollama_models(db, backend, names)


async def _fetch_ollama_tags(backend: ModelBackend) -> dict[str, Any]:
    base_url = _normalize_backend_base_url(backend.base_url, "ollama")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{base_url}/api/tags")
        response.raise_for_status()
        return response.json()


async def _resolve_ollama_model_name(backend: ModelBackend, model_name: str) -> str:
    base_url = _normalize_backend_base_url(backend.base_url, "ollama")
    async with httpx.AsyncClient(timeout=20) as client:
        return await _resolve_ollama_model_name_from_tags(client, base_url, model_name)


async def _fetch_ollama_capabilities(backend: ModelBackend, model_name: str) -> dict[str, Any]:
    base_url = _normalize_backend_base_url(backend.base_url, "ollama")
    capabilities = {"text": True, "vision": False, "tool_calling": False}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resolved_model_name = await _resolve_ollama_model_name_from_tags(client, base_url, model_name)
            response = await client.post(f"{base_url}/api/show", json={"model": resolved_model_name})
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return capabilities

    declared_capabilities = [str(item).lower() for item in payload.get("capabilities") or []]
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    families = [str(item).lower() for item in details.get("families") or []]
    model_info = payload.get("model_info") if isinstance(payload.get("model_info"), dict) else {}
    model_info_keys = " ".join(str(key).lower() for key in model_info.keys())
    model_info_values = " ".join(str(value).lower() for value in model_info.values() if isinstance(value, str))

    capabilities["vision"] = (
        "vision" in declared_capabilities
        or "clip" in families
        or "projector" in model_info_keys
        or "vision" in model_info_keys
        or "clip" in model_info_keys
        or "vision" in model_info_values
    )
    capabilities["tool_calling"] = any(item in declared_capabilities for item in ["tools", "tool", "tool_calling", "function_calling"])
    return capabilities


async def _resolve_ollama_model_name_from_tags(client: httpx.AsyncClient, base_url: str, model_name: str) -> str:
    candidate = (model_name or "").strip()
    if not candidate:
        return candidate
    response = await client.get(f"{base_url}/api/tags")
    response.raise_for_status()
    for item in response.json().get("models", []):
        names = [item.get("name"), item.get("model")]
        name = next((str(value).strip() for value in names if value and str(value).strip()), None)
        if not name:
            continue
        digest = str(item.get("digest") or "").strip()
        if candidate == name or candidate == item.get("model"):
            return name
        if digest and (digest.startswith(candidate) or candidate.startswith(digest)):
            return name
    return candidate


async def _refresh_ollama_capabilities_for_rows(db: AsyncSession, rows: list[tuple[ModelRegistry, ModelBackend]]) -> None:
    changed = False
    for model, backend in rows:
        if backend.backend_type != "ollama":
            continue
        try:
            capabilities = await _fetch_ollama_capabilities(backend, model.model_name)
        except Exception:
            continue
        effective = _normalize_capabilities(model.model_name, model.display_name, {**(model.capabilities or {}), **capabilities}, model.is_multimodal)
        if effective != (model.capabilities or {}) or model.is_multimodal != effective.get("vision", False):
            model.capabilities = effective
            model.is_multimodal = effective.get("vision", False)
            changed = True
    if changed:
        await db.commit()


def _status_request(backend: ModelBackend) -> tuple[str, dict[str, str]]:
    base_url = _normalize_backend_base_url(backend.base_url, backend.backend_type)
    headers = {}
    api_key = decrypt_api_key(backend.api_key_encrypted)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if backend.backend_type == "ollama":
        return f"{base_url}/api/tags", headers
    if backend.backend_type in {"openai", "vllm", "custom"}:
        return f"{base_url}/models", headers
    if backend.backend_type == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
        return f"{base_url}/v1/models" if not base_url.endswith("/v1") else f"{base_url}/models", headers
    return base_url, headers


def _normalize_backend_base_url(base_url: str, backend_type: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    if backend_type == "ollama" and normalized.endswith("/api"):
        normalized = normalized[:-4].rstrip("/")
    return normalized


def _backend_status_response(
    backend: ModelBackend,
    ok: bool,
    message: str,
    latency_ms: int | None,
    quota_warning: bool = False,
    quota_message: str | None = None,
) -> dict[str, Any]:
    return {
        "backend_id": str(backend.id),
        "name": backend.name,
        "type": backend.backend_type,
        "ok": ok,
        "message": message,
        "latency_ms": latency_ms,
        "quota_warning": quota_warning,
        "quota_message": quota_message,
    }


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("type") or payload)
            if error:
                return str(error)
            return str(payload.get("message") or payload.get("detail") or payload)
    except Exception:
        pass
    return f"HTTP {response.status_code}: {response.text[:200]}"


def _normalize_capabilities(model_name: str | None, display_name: str | None, capabilities: dict[str, Any], is_multimodal: bool = False) -> dict[str, Any]:
    normalized = {"text": True, **(capabilities or {})}
    if is_multimodal:
        normalized["vision"] = True
    return normalized


def _is_quota_error(response: httpx.Response, message: str) -> bool:
    return response.status_code in {402, 429} or _is_quota_message(message)


def _is_quota_message(message: str) -> bool:
    lowered = message.lower()
    keywords = ["quota", "insufficient", "billing", "balance", "credit", "额度", "余额", "计费", "欠费"]
    return any(keyword in lowered for keyword in keywords)


async def _clear_default_flags(
    db: AsyncSession,
    data: dict[str, Any],
    exclude_model_id: str | None = None,
) -> None:
    flag_fields = ["is_default_text", "is_default_embed", "is_default_vision"]
    for field in flag_fields:
        if data.get(field) is True:
            stmt = update(ModelRegistry).where(getattr(ModelRegistry, field).is_(True))
            if exclude_model_id:
                stmt = stmt.where(ModelRegistry.id != UUID(exclude_model_id))
            await db.execute(stmt.values({field: False}))
