"""
Knowledge base API.
Based on need.md: backend/app/api/knowledge.py
"""
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin_user
from app.database import get_db
from app.models import User
from app.schemas.knowledge import (
    ChunkListResponse,
    ChunkResponse,
    ChunkUpdate,
    DocumentCollectionUpdate,
    DocumentListResponse,
    DocumentResponse,
    DocumentTitleUpdate,
    DocumentVisibilityUpdate,
    KnowledgeCollectionCreate,
    KnowledgeCollectionListResponse,
    KnowledgeCollectionResponse,
    KnowledgeCollectionUpdate,
    UploadPolicyResponse,
    UrlIngestRequest,
)
from app.services import knowledge_service
from app.services.audit_service import record_audit_event
from app.config import settings

try:
    from app.tasks.knowledge_tasks import process_document_task
except Exception as exc:
    logging.getLogger(__name__).warning("Celery knowledge task unavailable, will use FastAPI BackgroundTasks: %s", exc)
    process_document_task = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])
admin_router = APIRouter(prefix="/api/admin/knowledge", tags=["知识库管理"], dependencies=[Depends(require_admin_user)])


DOCUMENT_QUEUE = "knowledge_documents"
URL_QUEUE = "knowledge_urls"


def dispatch_document_processing(background_tasks: BackgroundTasks, document_id: str, queue: str = DOCUMENT_QUEUE) -> None:
    if process_document_task is not None:
        try:
            async_result = process_document_task.apply_async(args=[document_id], queue=queue)
            logger.info("Dispatched knowledge document %s to Celery task %s on queue %s", document_id, async_result.id, queue)
            return
        except Exception as exc:
            logger.warning("Failed to dispatch knowledge document %s to Celery, fallback to BackgroundTasks: %s", document_id, exc)
    else:
        logger.warning("Celery task is unavailable, fallback knowledge document %s to BackgroundTasks", document_id)
    background_tasks.add_task(knowledge_service.process_document_by_id, document_id)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = None,
    is_public: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await knowledge_service.list_documents(db, current_user, status, is_public, skip, limit)


@router.get("/upload-policy", response_model=UploadPolicyResponse)
async def get_upload_policy(current_user: User = Depends(get_current_user)):
    return {
        "allowed_extensions": sorted(knowledge_service.ALLOWED_FILE_TYPES),
        "max_file_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "max_file_size_bytes": settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
        "max_files_per_batch": 20,
    }


@router.get("/collections", response_model=KnowledgeCollectionListResponse)
async def list_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await knowledge_service.list_collections(db)


@router.post("/collections", response_model=KnowledgeCollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    payload: KnowledgeCollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response = await knowledge_service.create_collection(db, payload.name, current_user.id, payload.description)
    await record_audit_event(db, "knowledge_collection_create", current_user.id, "knowledge_collection", response["id"], {"name": response["name"]})
    return response


@router.put("/collections/{collection_id}", response_model=KnowledgeCollectionResponse)
async def update_collection(
    collection_id: str,
    payload: KnowledgeCollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = await knowledge_service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="知识库不存在")
    try:
        response = await knowledge_service.update_collection(db, collection, payload.name, payload.description)
        await record_audit_event(db, "knowledge_collection_update", current_user.id, "knowledge_collection", collection_id, {"name": payload.name})
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    delete_documents: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = await knowledge_service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="知识库不存在")
    collection_name = collection.name
    await knowledge_service.delete_collection(db, collection, delete_documents)
    await record_audit_event(db, "knowledge_collection_delete", current_user.id, "knowledge_collection", collection_id, {"name": collection_name, "delete_documents": delete_documents})
    if delete_documents:
        return {"message": "知识库及其中资料已删除"}
    return {"message": "知识库已删除，原资料已移至未加入知识库"}


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    collection_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        document = await knowledge_service.upload_document(db, file, current_user.id, is_public if current_user.role == "admin" else False, collection_name=collection_name, process_immediately=False)
        dispatch_document_processing(background_tasks, document["id"], DOCUMENT_QUEUE)
        await record_audit_event(db, "doc_upload", current_user.id, "document", document["id"], {"filename": document["filename"], "file_type": document["file_type"], "is_public": document["is_public"]})
        return document
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/documents/uploads", response_model=list[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    is_public: bool = Form(False),
    collection_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="单次最多上传 20 个文件")
    try:
        uploaded = []
        for file in files:
            document = await knowledge_service.upload_document(db, file, current_user.id, is_public if current_user.role == "admin" else False, collection_name=collection_name, process_immediately=False)
            dispatch_document_processing(background_tasks, document["id"], DOCUMENT_QUEUE)
            await record_audit_event(db, "doc_upload", current_user.id, "document", document["id"], {"filename": document["filename"], "file_type": document["file_type"], "is_public": document["is_public"]})
            uploaded.append(document)
        return uploaded
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/documents/urls", response_model=list[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def ingest_urls(
    background_tasks: BackgroundTasks,
    payload: UrlIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        documents = await knowledge_service.ingest_urls(db, payload.urls, current_user.id, payload.is_public if current_user.role == "admin" else False, collection_name=payload.collection_name, process_immediately=False)
        for document in documents:
            dispatch_document_processing(background_tasks, document["id"], URL_QUEUE)
            await record_audit_event(db, "url_ingest", current_user.id, "document", document["id"], {"url": document["file_path"], "is_public": document["is_public"]})
        return documents
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/documents/{document_id}/visibility", response_model=DocumentResponse)
async def update_document_visibility(
    document_id: str,
    payload: DocumentVisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以设置公共文档")
    document = await knowledge_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    response = await knowledge_service.update_visibility(db, document, payload.is_public)
    await record_audit_event(db, "doc_visibility_update", current_user.id, "document", document_id, {"is_public": payload.is_public})
    return response


@router.put("/documents/{document_id}/title", response_model=DocumentResponse)
async def update_document_title(
    document_id: str,
    payload: DocumentTitleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await knowledge_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not knowledge_service.can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权修改该文档")
    response = await knowledge_service.update_title(db, document, payload.filename)
    await record_audit_event(db, "doc_title_update", current_user.id, "document", document_id, {"filename": payload.filename})
    return response


@router.put("/documents/{document_id}/collection", response_model=DocumentResponse)
async def update_document_collection(
    document_id: str,
    payload: DocumentCollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await knowledge_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not knowledge_service.can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权归档该文档")
    try:
        response = await knowledge_service.update_document_collection(db, document, payload.collection_id, payload.collection_name, current_user.id)
        await record_audit_event(db, "doc_collection_update", current_user.id, "document", document_id, {"collection_id": payload.collection_id, "collection_name": payload.collection_name})
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/documents/{document_id}/chunks", response_model=ChunkListResponse)
async def list_document_chunks(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await knowledge_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not knowledge_service.can_view_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权查看该文档")
    return await knowledge_service.list_chunks(db, document)


@router.put("/chunks/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: str,
    payload: ChunkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunk = await knowledge_service.get_chunk(db, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="分段不存在")
    document = await knowledge_service.get_document(db, str(chunk.document_id))
    if not document or not knowledge_service.can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权修改该分段")
    response = await knowledge_service.update_chunk(db, chunk, payload.chunk_text)
    await record_audit_event(db, "doc_chunk_update", current_user.id, "doc_chunk", chunk_id, {"document_id": str(chunk.document_id)})
    return response


@router.delete("/chunks/{chunk_id}")
async def delete_chunk(
    chunk_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunk = await knowledge_service.get_chunk(db, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="分段不存在")
    document = await knowledge_service.get_document(db, str(chunk.document_id))
    if not document or not knowledge_service.can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权删除该分段")
    await knowledge_service.delete_chunk(db, chunk)
    await record_audit_event(db, "doc_chunk_delete", current_user.id, "doc_chunk", chunk_id, {"document_id": str(document.id)})
    return {"message": "分段已删除"}


@router.post("/documents/{document_id}/retry", response_model=DocumentResponse)
async def retry_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await knowledge_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not knowledge_service.can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权重新处理该文档")
    response = await knowledge_service.mark_document_for_retry(db, document)
    dispatch_document_processing(background_tasks, document_id, URL_QUEUE if document.file_type == "url" else DOCUMENT_QUEUE)
    await record_audit_event(db, "doc_retry", current_user.id, "document", document_id, {"file_type": document.file_type})
    return response


@router.post("/documents/reindex")
async def reindex_all_documents(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以批量重新索引知识库")
    documents = (await knowledge_service.list_documents(db, current_user=current_user, limit=10000)).get("documents", [])
    for document in documents:
        response = await knowledge_service.mark_document_for_retry(db, await knowledge_service.get_document(db, document["id"]))
        dispatch_document_processing(background_tasks, response["id"], URL_QUEUE if response["file_type"] == "url" else DOCUMENT_QUEUE)
    await record_audit_event(db, "doc_reindex_all", current_user.id, "document", None, {"total": len(documents)})
    return {"message": "已提交全部文档重新索引任务", "total": len(documents)}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await knowledge_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not knowledge_service.can_manage_document(current_user, document):
        raise HTTPException(status_code=403, detail="无权删除该文档")
    filename = document.filename
    await knowledge_service.delete_document(db, document)
    await record_audit_event(db, "doc_delete", current_user.id, "document", document_id, {"filename": filename})
    return {"message": "文档已删除"}


admin_router.include_router(router, prefix="")
