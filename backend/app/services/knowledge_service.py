"""
Knowledge base service.
Based on need.md: backend/app/services/knowledge_service.py
"""
from pathlib import Path
import json
import re
import tempfile
import warnings
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from uuid import UUID, uuid4
import time

import httpx
from fastapi import UploadFile
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import DocChunk, Document, KnowledgeCollection
from app.utils.sanitizer import sanitize_text
from app.utils.notification import notification_service
from app.utils.redis_client import get_redis_client

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "knowledge"
IMAGE_FILE_TYPES = {"png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"}
ALLOWED_FILE_TYPES = {"pdf", "docx", "txt", "md", "html", "xlsx", *IMAGE_FILE_TYPES}
MAX_IMAGE_PIXELS = 50_000_000
PROCESSING_PROGRESS_TTL_SECONDS = 3600
PROCESSING_PROGRESS_KEY_PREFIX = "knowledge:progress:"
URL_FETCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 CampusAgentBot/1.0"
)
URL_FETCH_HEADERS = {
    "User-Agent": URL_FETCH_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}


def _document_response(document: Document, collection: KnowledgeCollection | None = None) -> dict[str, Any]:
    return {
        "id": str(document.id),
        "filename": document.filename,
        "file_type": document.file_type,
        "file_path": document.file_path,
        "collection_id": str(document.collection_id) if document.collection_id else None,
        "collection_name": collection.name if collection else None,
        "file_size": _document_file_size(document),
        "uploaded_by": str(document.uploaded_by) if document.uploaded_by else None,
        "is_public": document.is_public,
        "status": document.status,
        "error_message": document.error_message,
        "processing_progress": _read_processing_progress(document),
        "created_at": document.created_at,
    }


def _document_file_size(document: Document) -> int | None:
    if document.file_type == "url":
        return None
    try:
        path = Path(document.file_path)
        if path.exists() and path.is_file():
            return path.stat().st_size
    except Exception:
        return None
    return None


async def list_documents(
    db: AsyncSession,
    current_user=None,
    status: str | None = None,
    is_public: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    await ensure_knowledge_collection_schema(db)
    query = select(Document).order_by(Document.created_at.desc())
    if current_user is not None and current_user.role != "admin":
        query = query.where(or_(Document.uploaded_by == current_user.id, Document.is_public.is_(True)))
    if status:
        query = query.where(Document.status == status)
    if is_public is not None:
        query = query.where(Document.is_public == is_public)
    result = await db.execute(query.offset(skip).limit(limit))
    documents = result.scalars().all()
    collection_ids = [doc.collection_id for doc in documents if doc.collection_id]
    collections = await _collections_by_id(db, collection_ids)
    return {"total": len(documents), "documents": [_document_response(doc, collections.get(doc.collection_id)) for doc in documents]}


async def list_collections(db: AsyncSession) -> dict[str, Any]:
    await ensure_knowledge_collection_schema(db)
    result = await db.execute(select(KnowledgeCollection).order_by(func.lower(KnowledgeCollection.name)))
    collections = result.scalars().all()
    return {"total": len(collections), "collections": [_collection_response(collection) for collection in collections]}


async def create_collection(
    db: AsyncSession,
    name: str,
    created_by: UUID | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    await ensure_knowledge_collection_schema(db)
    collection = await get_or_create_collection(db, name, created_by, description)
    await db.commit()
    await db.refresh(collection)
    return _collection_response(collection)


async def get_collection(db: AsyncSession, collection_id: str) -> KnowledgeCollection | None:
    await ensure_knowledge_collection_schema(db)
    result = await db.execute(select(KnowledgeCollection).where(KnowledgeCollection.id == UUID(collection_id)))
    return result.scalar_one_or_none()


async def update_collection(
    db: AsyncSession,
    collection: KnowledgeCollection,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    clean_name = sanitize_text(name or "").strip()
    if not clean_name:
        raise ValueError("知识库名称不能为空")
    result = await db.execute(
        select(KnowledgeCollection).where(
            func.lower(KnowledgeCollection.name) == clean_name.lower(),
            KnowledgeCollection.id != collection.id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("同名知识库已存在")
    collection.name = clean_name
    collection.description = sanitize_text(description or "") or None
    await db.commit()
    await db.refresh(collection)
    return _collection_response(collection)


async def delete_collection(db: AsyncSession, collection: KnowledgeCollection, delete_documents: bool = False) -> None:
    if delete_documents:
        result = await db.execute(select(Document).where(Document.collection_id == collection.id))
        for document in result.scalars().all():
            path = Path(document.file_path)
            if document.file_type != "url" and path.exists() and path.is_file():
                path.unlink()
            await db.delete(document)
    else:
        await db.execute(
            text("UPDATE documents SET collection_id = NULL WHERE collection_id = :collection_id"),
            {"collection_id": collection.id},
        )
    await db.delete(collection)
    await db.commit()


async def get_or_create_collection(
    db: AsyncSession,
    name: str | None,
    created_by: UUID | None = None,
    description: str | None = None,
) -> KnowledgeCollection | None:
    await ensure_knowledge_collection_schema(db)
    clean_name = sanitize_text(name or "").strip()
    if not clean_name:
        return None
    result = await db.execute(select(KnowledgeCollection).where(func.lower(KnowledgeCollection.name) == clean_name.lower()))
    collection = result.scalar_one_or_none()
    if collection:
        return collection
    collection = KnowledgeCollection(name=clean_name, description=sanitize_text(description or "") or None, created_by=created_by)
    db.add(collection)
    await db.flush()
    return collection


async def update_document_collection(
    db: AsyncSession,
    document: Document,
    collection_id: str | None = None,
    collection_name: str | None = None,
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    await ensure_knowledge_collection_schema(db)
    collection = None
    if collection_id:
        result = await db.execute(select(KnowledgeCollection).where(KnowledgeCollection.id == UUID(collection_id)))
        collection = result.scalar_one_or_none()
        if not collection:
            raise ValueError("知识库不存在")
    elif collection_name and collection_name.strip():
        collection = await get_or_create_collection(db, collection_name, current_user_id)
    document.collection_id = collection.id if collection else None
    await db.commit()
    await db.refresh(document)
    return _document_response(document, collection)


async def upload_document(
    db: AsyncSession,
    file: UploadFile,
    uploaded_by: UUID,
    is_public: bool = False,
    collection_name: str | None = None,
    process_immediately: bool = True,
) -> dict[str, Any]:
    await ensure_knowledge_collection_schema(db)
    filename = sanitize_text(file.filename or "untitled")
    file_type = _file_type(filename)
    if file_type not in ALLOWED_FILE_TYPES:
        raise ValueError("仅支持 PDF、DOCX、TXT、Markdown、HTML、XLSX 和常见图片文件")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValueError(f"文件不能超过 {settings.MAX_UPLOAD_SIZE_MB}MB")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4()}_{filename}".replace("..", "_").replace("/", "_").replace("\\", "_")
    storage_path = UPLOAD_DIR / safe_name
    suffix = 1
    while storage_path.exists():
        storage_path = UPLOAD_DIR / f"{suffix}_{safe_name}"
        suffix += 1
    storage_path.write_bytes(content)

    collection = await get_or_create_collection(db, collection_name, uploaded_by)
    document = Document(
        filename=filename,
        file_type=file_type,
        file_path=str(storage_path),
        collection_id=collection.id if collection else None,
        uploaded_by=uploaded_by,
        is_public=is_public,
        status="processing",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    _broadcast_document_event("knowledge_document_created", document)
    if process_immediately:
        await process_document(db, document)
    return _document_response(document, collection)


async def ingest_urls(
    db: AsyncSession,
    urls: list[str],
    uploaded_by: UUID,
    is_public: bool = False,
    collection_name: str | None = None,
    process_immediately: bool = True,
) -> list[dict[str, Any]]:
    await ensure_knowledge_collection_schema(db)
    created = []
    collection = await get_or_create_collection(db, collection_name, uploaded_by)
    for url in urls:
        clean_url = sanitize_text(url)
        if not clean_url.startswith(("http://", "https://")):
            raise ValueError(f"URL 不合法：{url}")
        document = Document(
            filename=clean_url,
            file_type="url",
            file_path=clean_url,
            collection_id=collection.id if collection else None,
            uploaded_by=uploaded_by,
            is_public=is_public,
            status="processing",
        )
        db.add(document)
        created.append(document)
    await db.commit()
    for document in created:
        await db.refresh(document)
        if process_immediately:
            await process_document(db, document)
    return [_document_response(document, collection) for document in created]


async def _collections_by_id(db: AsyncSession, collection_ids: list[UUID]) -> dict[UUID, KnowledgeCollection]:
    if not collection_ids:
        return {}
    result = await db.execute(select(KnowledgeCollection).where(KnowledgeCollection.id.in_(collection_ids)))
    return {collection.id: collection for collection in result.scalars().all()}


def _collection_response(collection: KnowledgeCollection) -> dict[str, Any]:
    return {
        "id": str(collection.id),
        "name": collection.name,
        "description": collection.description,
        "created_by": str(collection.created_by) if collection.created_by else None,
        "created_at": collection.created_at,
    }


async def ensure_knowledge_collection_schema(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS knowledge_collections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) UNIQUE NOT NULL,
            description TEXT,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await db.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS collection_id UUID REFERENCES knowledge_collections(id) ON DELETE SET NULL
    """))
    await db.execute(text("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_file_type_check"))
    await db.execute(text("""
        ALTER TABLE documents
        ADD CONSTRAINT documents_file_type_check
        CHECK (file_type IN ('pdf', 'docx', 'txt', 'md', 'html', 'xlsx', 'url', 'png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'))
    """))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_knowledge_collections_name ON knowledge_collections(LOWER(name))"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id, created_at DESC)"))
    await db.commit()


async def process_document_by_id(document_id: str) -> None:
    async with AsyncSessionLocal() as db:
        document = await get_document(db, document_id)
        if document:
            await process_document(db, document)


async def get_document(db: AsyncSession, document_id: str) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
    return result.scalar_one_or_none()


def can_manage_document(user, document: Document) -> bool:
    return user.role == "admin" or document.uploaded_by == user.id


def can_view_document(user, document: Document) -> bool:
    return can_manage_document(user, document) or document.is_public


async def update_visibility(db: AsyncSession, document: Document, is_public: bool) -> dict[str, Any]:
    document.is_public = is_public
    await db.commit()
    await db.refresh(document)
    return _document_response(document)


async def update_title(db: AsyncSession, document: Document, filename: str) -> dict[str, Any]:
    document.filename = sanitize_text(filename)
    await db.commit()
    await db.refresh(document)
    return _document_response(document)


def _chunk_response(chunk: DocChunk) -> dict[str, Any]:
    return {
        "id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "chunk_index": chunk.chunk_index,
        "chunk_text": chunk.chunk_text,
        "metadata": chunk.meta_info,
        "created_at": chunk.created_at,
    }


async def list_chunks(db: AsyncSession, document: Document) -> dict[str, Any]:
    result = await db.execute(
        select(DocChunk)
        .where(DocChunk.document_id == document.id)
        .order_by(DocChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return {"total": len(chunks), "chunks": [_chunk_response(chunk) for chunk in chunks]}


async def get_chunk(db: AsyncSession, chunk_id: str) -> DocChunk | None:
    result = await db.execute(select(DocChunk).where(DocChunk.id == UUID(chunk_id)))
    return result.scalar_one_or_none()


async def update_chunk(db: AsyncSession, chunk: DocChunk, chunk_text: str) -> dict[str, Any]:
    embedding = _embed_texts([chunk_text])[0]
    await db.execute(
        text(
            """
            UPDATE doc_chunks
            SET chunk_text = :chunk_text, embedding = CAST(:embedding AS vector)
            WHERE id = :chunk_id
            """
        ),
        {
            "chunk_text": chunk_text,
            "embedding": _format_embedding(embedding),
            "chunk_id": chunk.id,
        },
    )
    await db.commit()
    updated = await get_chunk(db, str(chunk.id))
    return _chunk_response(updated)


async def search_public_chunks(db: AsyncSession, query: str, limit: int = 5, collection_ids: list[str] | None = None) -> list[dict[str, Any]]:
    query = sanitize_text(query or "").strip()
    if not query:
        return []
    embedding = _embed_texts([query])[0]
    collection_filter = ""
    params: dict[str, Any] = {"embedding": _format_embedding(embedding), "limit": limit}
    if collection_ids:
        collection_filter = "AND d.collection_id = ANY(CAST(:collection_ids AS uuid[]))"
        params["collection_ids"] = collection_ids
    result = await db.execute(
        text(
            f"""
            SELECT c.id,
                   c.document_id,
                   c.chunk_index,
                   c.chunk_text,
                   c.metadata,
                   d.filename,
                   d.file_type,
                   1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM doc_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'ready' AND d.is_public = TRUE
              {collection_filter}
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        ),
        params,
    )
    sources = []
    for row in result.mappings().all():
        text_value = row["chunk_text"] or ""
        sources.append({
            "id": str(row["id"]),
            "document_id": str(row["document_id"]),
            "chunk_index": row["chunk_index"],
            "filename": row["filename"],
            "file_type": row["file_type"],
            "snippet": text_value[:360],
            "score": float(row["score"] or 0),
            "metadata": row["metadata"] or {},
        })
    return sources


async def delete_chunk(db: AsyncSession, chunk: DocChunk) -> None:
    document_id = chunk.document_id
    await db.delete(chunk)
    await db.commit()
    await _renumber_chunks(db, document_id)


async def _renumber_chunks(db: AsyncSession, document_id: UUID) -> None:
    result = await db.execute(
        select(DocChunk)
        .where(DocChunk.document_id == document_id)
        .order_by(DocChunk.chunk_index)
    )
    for index, chunk in enumerate(result.scalars().all()):
        chunk.chunk_index = index
    await db.commit()


async def delete_document(db: AsyncSession, document: Document) -> None:
    path = Path(document.file_path)
    if document.file_type != "url" and path.exists() and path.is_file():
        path.unlink()
    await db.delete(document)
    await db.commit()


async def retry_document(db: AsyncSession, document: Document) -> dict[str, Any]:
    document.status = "processing"
    document.error_message = None
    await db.commit()
    await db.refresh(document)
    await process_document(db, document)
    return _document_response(document)


async def mark_document_for_retry(db: AsyncSession, document: Document) -> dict[str, Any]:
    document.status = "processing"
    document.error_message = None
    await db.commit()
    await db.refresh(document)
    return _document_response(document)


async def process_document(db: AsyncSession, document: Document) -> None:
    progress_key = str(document.id)
    try:
        _set_processing_progress(progress_key, "准备处理文档", percent=2)
        await _delete_existing_chunks(db, document)
        if document.file_type == "url":
            _set_processing_progress(progress_key, "抓取网页正文", percent=10)
            text = await _fetch_url(document.file_path)
        elif document.file_type in {"txt", "md", "html"}:
            _set_processing_progress(progress_key, "读取文本文件", percent=15)
            text = Path(document.file_path).read_text(encoding="utf-8", errors="ignore")
        elif document.file_type in {"pdf", "docx", "xlsx", *IMAGE_FILE_TYPES}:
            text = _extract_binary_document_text(document)
        else:
            raise ValueError("不支持的文档类型")
        _set_processing_progress(progress_key, "分词分块", percent=72)
        chunks = _split_text(text)
        if not chunks:
            raise ValueError("未提取到可用于知识库的文本")
        _set_processing_progress(progress_key, "生成向量", percent=82)
        embeddings = _embed_texts(chunks)
        for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            await _insert_chunk(db, document, index, chunk_text, embedding)
        document.status = "ready"
        document.error_message = None
        _set_processing_progress(progress_key, "处理完成", percent=100)
    except Exception as exc:
        document.status = "error"
        document.error_message = str(exc)[:1000]
        _set_processing_progress(progress_key, "处理失败", percent=100)
    finally:
        _cleanup_uploaded_file(document)
    await db.commit()
    await db.refresh(document)
    _broadcast_document_event("knowledge_document_processed", document)
    _expire_processing_progress()


def _cleanup_uploaded_file(document: Document) -> None:
    if document.file_type == "url" or not document.file_path:
        return
    try:
        path = Path(document.file_path)
        upload_root = UPLOAD_DIR.resolve()
        resolved = path.resolve()
        if upload_root in resolved.parents and resolved.exists() and resolved.is_file():
            resolved.unlink()
            document.file_path = ""
    except Exception:
        pass


async def _fetch_url(url: str) -> None:
    await _enforce_url_fetch_policy(url)
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=URL_FETCH_HEADERS)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type or "html" in content_type:
            return _extract_html_text(response.text)
        return response.text


async def _enforce_url_fetch_policy(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"URL 不合法：{url}")
    await _check_robots_txt(parsed, url)
    _rate_limit_url_host(parsed.netloc.lower())


async def _check_robots_txt(parsed, url: str) -> None:
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            response = await client.get(robots_url, headers=URL_FETCH_HEADERS)
        if response.status_code >= 400:
            return
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        if not parser.can_fetch(URL_FETCH_USER_AGENT, url):
            raise ValueError(f"robots.txt 禁止抓取该 URL：{url}")
    except ValueError:
        raise
    except Exception:
        return


def _rate_limit_url_host(host: str) -> None:
    try:
        redis_client = get_redis_client()
        key = f"knowledge:url_fetch:{host}"
        now = int(time.time())
        previous = redis_client.get(key)
        min_interval = 5
        if previous and now - int(previous) < min_interval:
            raise ValueError(f"网页抓取频率过高：{host}，请稍后再试")
        redis_client.setex(key, min_interval, now)
    except ValueError:
        raise
    except Exception:
        return


def cleanup_stale_uploads(max_age_seconds: int = 3600) -> int:
    if not UPLOAD_DIR.exists():
        return 0
    deleted = 0
    now = time.time()
    for path in UPLOAD_DIR.iterdir():
        try:
            if path.is_file() and now - path.stat().st_mtime > max_age_seconds:
                path.unlink()
                deleted += 1
        except Exception:
            continue
    return deleted


class _ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        text_value = data.strip()
        if text_value:
            self.parts.append(text_value)


def _extract_html_text(html: str) -> str:
    parser = _ReadableHTMLParser()
    parser.feed(html)
    text_value = " ".join(parser.parts)
    text_value = re.sub(r"\s+", " ", text_value)
    text_value = re.sub(r"\s*\n\s*", "\n", text_value)
    return text_value.strip()


async def _delete_existing_chunks(db: AsyncSession, document: Document) -> None:
    await db.execute(delete(DocChunk).where(DocChunk.document_id == document.id))


async def _insert_chunk(
    db: AsyncSession,
    document: Document,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float],
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO doc_chunks (document_id, chunk_index, chunk_text, embedding, metadata)
            VALUES (:document_id, :chunk_index, :chunk_text, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            """
        ),
        {
            "document_id": document.id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "embedding": _format_embedding(embedding),
            "metadata": json.dumps({"source": document.filename, "file_type": document.file_type}, ensure_ascii=False),
        },
    )


def _extract_binary_document_text(document: Document) -> str:
    path = Path(document.file_path)
    progress_key = str(document.id)
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError("文件为空或不存在")
    if document.file_type == "pdf":
        _set_processing_progress(progress_key, "提取 PDF 文本层", percent=8)
        text_value = _extract_pdf_text_with_pypdf(path)
        if len(text_value.strip()) < 20:
            text_value = _extract_pdf_text_with_pymupdf(path)
        if len(text_value.strip()) < 20:
            text_value = _extract_pdf_text_with_paddleocr(path, progress_key)
        if len(text_value.strip()) < 20:
            text_value = _extract_pdf_text_with_ocr(path)
        if len(text_value.strip()) < 20:
            raise ValueError("未检测到可提取的 PDF 文本层，OCR 也未识别到有效文字。该 PDF 可能清晰度较低、页面为图片或暂不支持。")
        return text_value
    if document.file_type == "docx":
        _set_processing_progress(progress_key, "读取 DOCX 文档", percent=12)
        from docx import Document as DocxDocument
        doc = DocxDocument(str(path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    if document.file_type == "xlsx":
        _set_processing_progress(progress_key, "读取 XLSX 表格", percent=12)
        return _extract_xlsx_text(path)
    if document.file_type in IMAGE_FILE_TYPES:
        _set_processing_progress(progress_key, "图片 OCR 识别", percent=15)
        text_value = _extract_image_text_with_paddleocr(path)
        if len(text_value.strip()) < 20:
            raise ValueError("图片 OCR 未识别到有效文字。请确认图片清晰、方向正确且包含可识别文字。")
        return text_value
    return ""


def _extract_pdf_text_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ""
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _extract_pdf_text_with_pymupdf(path: Path) -> str:
    try:
        fitz = _import_pymupdf()
        parts = []
        with fitz.open(str(path)) as doc:
            for page in doc:
                parts.append(page.get_text("text") or "")
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_pdf_text_with_ocr(path: Path) -> str:
    try:
        fitz = _import_pymupdf()
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        parts = []
        with fitz.open(str(path)) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                result, _ = ocr(pix.tobytes("png"))
                if result:
                    parts.extend(item[1] for item in result if len(item) > 1 and item[1])
        return "\n".join(parts)
    except Exception as exc:
        return ""


_paddle_ocr = None


def _get_paddle_ocr():
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR
        try:
            _paddle_ocr = PaddleOCR(lang="ch", device="cpu")
        except TypeError:
            _paddle_ocr = PaddleOCR(lang="ch", use_gpu=False)
    return _paddle_ocr


def _extract_pdf_text_with_paddleocr(path: Path, progress_key: str | None = None) -> str:
    try:
        fitz = _import_pymupdf()
        ocr = _get_paddle_ocr()
        parts = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with fitz.open(str(path)) as doc:
                total_pages = len(doc)
                for page_index, page in enumerate(doc, start=1):
                    if progress_key:
                        percent = 15 + int((page_index - 1) / max(total_pages, 1) * 50)
                        _set_processing_progress(progress_key, f"PDF OCR 第 {page_index}/{total_pages} 页", percent=percent, page=page_index, total_pages=total_pages)
                    image_path = tmp_path / f"page_{page_index}.png"
                    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
                    pix.save(str(image_path))
                    result = ocr.predict(str(image_path))
                    parts.extend(_extract_paddleocr_texts(result))
                if progress_key:
                    _set_processing_progress(progress_key, f"PDF OCR 完成，共 {total_pages} 页", percent=66, page=total_pages, total_pages=total_pages)
        return "\n".join(parts)
    except Exception as exc:
        raise ValueError(f"PaddleOCR 处理 PDF 页面图片失败：{exc}") from exc


def _import_pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            if not hasattr(fitz, "open") or not hasattr(fitz, "Matrix"):
                raise ImportError("当前 fitz 不是 PyMuPDF")
            return fitz
        except ImportError as exc:
            raise ImportError("请安装 PyMuPDF，并移除错误的 fitz 包：pip uninstall fitz && pip install PyMuPDF") from exc


def _extract_image_text_with_paddleocr(path: Path) -> str:
    _validate_image_for_ocr(path)
    try:
        result = _get_paddle_ocr().predict(str(path))
        return "\n".join(_extract_paddleocr_texts(result))
    except Exception as exc:
        raise ValueError(f"PaddleOCR 处理图片失败：{exc}") from exc


def _validate_image_for_ocr(path: Path) -> None:
    from PIL import Image
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            image.verify()
            width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("图片尺寸异常，无法进行 OCR")
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError(f"图片像素过大，最大允许 {MAX_IMAGE_PIXELS} 像素")


def _extract_paddleocr_texts(result) -> list[str]:
    texts = []
    for res in result or []:
        if hasattr(res, "rec_texts"):
            rec_texts = res.rec_texts
            rec_scores = getattr(res, "rec_scores", [])
        elif isinstance(res, dict):
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
        elif isinstance(res, list):
            for line in res:
                if isinstance(line, list) and len(line) > 1 and isinstance(line[1], (list, tuple)):
                    text_value = str(line[1][0]).strip()
                    if text_value:
                        texts.append(text_value)
            continue
        else:
            continue

        for index, text_value in enumerate(rec_texts):
            text_value = str(text_value).strip()
            if not text_value:
                continue
            score = rec_scores[index] if index < len(rec_scores) else None
            if score is None or score >= 0.1:
                texts.append(text_value)
    return texts


def _set_processing_progress(
    document_id: str,
    message: str,
    percent: int,
    page: int | None = None,
    total_pages: int | None = None,
) -> None:
    progress = {
        "message": message,
        "percent": max(0, min(100, percent)),
        "page": page,
        "total_pages": total_pages,
    }
    try:
        get_redis_client().setex(
            f"{PROCESSING_PROGRESS_KEY_PREFIX}{document_id}",
            PROCESSING_PROGRESS_TTL_SECONDS,
            json.dumps(progress, ensure_ascii=False),
        )
    except Exception:
        pass


def _read_processing_progress(document: Document) -> dict[str, Any] | None:
    try:
        raw_progress = get_redis_client().get(f"{PROCESSING_PROGRESS_KEY_PREFIX}{document.id}")
        if raw_progress:
            return json.loads(raw_progress)
    except Exception:
        pass
    if document.status == "ready":
        return {"message": "处理完成", "percent": 100, "page": None, "total_pages": None}
    if document.status == "error":
        return {"message": "处理失败", "percent": 100, "page": None, "total_pages": None}
    return None


def _expire_processing_progress() -> None:
    # Redis setex handles progress cleanup.
    return


def _extract_xlsx_text(path: Path) -> str:
    from openpyxl import load_workbook
    workbook = load_workbook(str(path), read_only=True, data_only=True)
    parts = []
    for sheet in workbook.worksheets:
        parts.append(f"工作表：{sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            values = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if values:
                parts.append("\t".join(values))
    return "\n".join(parts)


def _split_text(text: str) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    pieces = _segment_text(normalized)
    tokenizer = _get_bert_tokenizer()
    chunk_tokens = max(settings.KNOWLEDGE_CHUNK_TOKENS, 64)
    overlap_tokens = min(settings.KNOWLEDGE_CHUNK_TOKEN_OVERLAP, chunk_tokens // 2)
    chunks = []
    current_parts = []
    current_token_count = 0

    for piece in pieces:
        piece_token_count = len(tokenizer.encode(piece, add_special_tokens=False))
        if current_parts and current_token_count + piece_token_count > chunk_tokens:
            chunks.append("".join(current_parts).strip())
            current_parts, current_token_count = _overlap_tail(current_parts, tokenizer, overlap_tokens)
        current_parts.append(piece)
        current_token_count += piece_token_count

    if current_parts:
        chunks.append("".join(current_parts).strip())
    if not chunks:
        return _split_text_by_chars(normalized)
    return chunks


def _segment_text(text: str) -> list[str]:
    try:
        import jieba
        tokens = list(jieba.cut(text, cut_all=False))
    except Exception:
        tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+|\s+|[^\w\s]", text)
    return [token for token in tokens if token]


_bert_tokenizer = None


def _get_bert_tokenizer():
    global _bert_tokenizer
    if _bert_tokenizer is None:
        from transformers import BertTokenizerFast
        tokenizer_path = Path(settings.BERT_MODEL_PATH)
        if not tokenizer_path.exists():
            raise ValueError(f"本地 BERT 分词模型不存在：{tokenizer_path}")
        _bert_tokenizer = BertTokenizerFast.from_pretrained(str(tokenizer_path))
    return _bert_tokenizer


def _overlap_tail(parts: list[str], tokenizer, overlap_tokens: int) -> tuple[list[str], int]:
    if overlap_tokens <= 0:
        return [], 0
    tail = []
    token_count = 0
    for piece in reversed(parts):
        piece_token_count = len(tokenizer.encode(piece, add_special_tokens=False))
        if tail and token_count + piece_token_count > overlap_tokens:
            break
        tail.insert(0, piece)
        token_count += piece_token_count
    return tail, token_count


def _split_text_by_chars(text: str) -> list[str]:
    chunk_size = max(settings.KNOWLEDGE_CHUNK_SIZE, 100)
    overlap = min(settings.KNOWLEDGE_CHUNK_OVERLAP, chunk_size // 2)
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        model_path = Path(settings.TEXT2VEC_MODEL_PATH)
        if not model_path.exists():
            raise ValueError(f"本地嵌入模型不存在：{model_path}")
        _embedding_model = SentenceTransformer(str(model_path))
    return _embedding_model


def _embed_texts(chunks: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    vectors = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]


def _format_embedding(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _broadcast_document_event(event_type: str, document: Document) -> None:
    notification_service.broadcast_knowledge_event({
        "type": event_type,
        "document_id": str(document.id),
        "filename": document.filename,
        "status": document.status,
        "is_public": document.is_public,
        "uploaded_by": str(document.uploaded_by) if document.uploaded_by else None,
    })


def _file_type(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
