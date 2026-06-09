"""Knowledge base Celery tasks."""
import asyncio
import logging

from app.celery_app import celery_app
from app.services.knowledge_service import process_document_by_id

logger = logging.getLogger(__name__)


if celery_app is not None:
    @celery_app.task(name="knowledge.process_document")
    def process_document_task(document_id: str) -> None:
        logger.info("Celery started knowledge document processing: %s", document_id)
        try:
            asyncio.run(process_document_by_id(document_id))
            logger.info("Celery finished knowledge document processing: %s", document_id)
        except Exception:
            logger.exception("Celery failed knowledge document processing: %s", document_id)
            raise
