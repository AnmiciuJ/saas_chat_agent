"""
知识库业务逻辑层。
"""

from typing import AsyncGenerator

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.knowledge import KnowledgeBase, Document, KnowledgeEntry
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeEntryCreate


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
        """接收文件元数据并落库，实际文件存储与离线处理由异步任务接管。"""
        content = await file.read()
        doc = Document(
            tenant_id=tenant_id,
            knowledge_base_id=kb_id,
            original_filename=file.filename or "untitled",
            storage_key=f"tenants/{tenant_id}/documents/{kb_id}/{file.filename}",
            size_bytes=len(content),
            mime_type=file.content_type,
        )
        self._db.add(doc)
        await self._db.flush()
        await self._db.refresh(doc)
        # TODO: 将文件内容写入对象存储，并派发离线入库任务
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
        # TODO: 派发条目分块与向量化任务
        return entry
