"""
知识库管理路由。
"""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_tenant_id
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    DocumentUploadOut,
    KnowledgeEntryCreate,
    KnowledgeEntryOut,
)
from app.schemas.common import PagedResponse, PageParams, SuccessResponse
from app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库管理"])


@router.post("", response_model=KnowledgeBaseOut, status_code=201)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建知识库。"""
    service = KnowledgeService(db)
    return await service.create_knowledge_base(tenant_id, payload)


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_knowledge_bases(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """列出当前租户的全部知识库。"""
    service = KnowledgeService(db)
    return await service.list_knowledge_bases(tenant_id)


@router.post("/{kb_id}/documents", response_model=DocumentUploadOut, status_code=201)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """向指定知识库上传文档。"""
    service = KnowledgeService(db)
    return await service.upload_document(tenant_id, kb_id, file)


@router.post("/{kb_id}/entries", response_model=KnowledgeEntryOut, status_code=201)
async def create_entry(
    kb_id: int,
    payload: KnowledgeEntryCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """向指定知识库添加手工条目。"""
    service = KnowledgeService(db)
    return await service.create_entry(tenant_id, kb_id, payload)
