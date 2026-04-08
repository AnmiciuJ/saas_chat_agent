"""
知识库业务逻辑层。
"""

import logging

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.knowledge import (
    KnowledgeBase, Document, KnowledgeEntry, IngestionJob,
)
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeEntryCreate
from app.services.storage import save_file

logger = logging.getLogger(__name__)


class KnowledgeService:
    """封装知识库、文档与条目的业务规则。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_knowledge_base(
        self, tenant_id: int, payload: KnowledgeBaseCreate
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
            embedding_model_key=payload.embedding_model_key,
        )
        self._db.add(kb)
        await self._db.flush()
        await self._db.refresh(kb)
        return kb

    async def list_knowledge_bases(self, tenant_id: int) -> list[KnowledgeBase]:
        result = await self._db.execute(
            select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def upload_document(
        self, tenant_id: int, kb_id: int, file: UploadFile
    ) -> Document:
        """接收文件、写入存储、落库元数据、派发离线入库任务。"""
        content = await file.read()
        filename = file.filename or "untitled"
        storage_key = f"tenants/{tenant_id}/documents/{kb_id}/{filename}"

        await save_file(storage_key, content)

        doc = Document(
            tenant_id=tenant_id,
            knowledge_base_id=kb_id,
            original_filename=filename,
            storage_key=storage_key,
            size_bytes=len(content),
            mime_type=file.content_type,
        )
        self._db.add(doc)
        await self._db.flush()
        await self._db.refresh(doc)

        job = IngestionJob(
            tenant_id=tenant_id,
            document_id=doc.id,
            job_type="full_pipeline",
            status="queued",
        )
        self._db.add(job)
        await self._db.flush()
        await self._db.refresh(job)

        from workers.tasks.knowledge_pipeline import run_document_ingestion
        task = run_document_ingestion.delay(tenant_id, doc.id)
        job.worker_task_id = task.id
        await self._db.flush()

        logger.info(
            "文档入库任务已派发: document_id=%s, task_id=%s",
            doc.id, task.id,
        )
        return doc

    async def create_entry(
        self, tenant_id: int, kb_id: int, payload: KnowledgeEntryCreate
    ) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            tenant_id=tenant_id,
            knowledge_base_id=kb_id,
            title=payload.title,
            body=payload.body,
        )
        self._db.add(entry)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry
