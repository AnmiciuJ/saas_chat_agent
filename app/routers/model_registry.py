"""
模型注册与绑定路由。
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_tenant_id
from app.models.model_registry import BaseModel_, EmbeddingModel, TenantModelBinding

router = APIRouter(prefix="/api/models", tags=["模型管理"])


@router.get("/base")
async def list_base_models(db: AsyncSession = Depends(get_db)):
    """列出平台可用的基座模型。"""
    result = await db.execute(
        select(BaseModel_).where(BaseModel_.is_active == True)
    )
    return list(result.scalars().all())


@router.get("/embedding")
async def list_embedding_models(db: AsyncSession = Depends(get_db)):
    """列出平台可用的嵌入模型。"""
    result = await db.execute(
        select(EmbeddingModel).where(EmbeddingModel.is_active == True)
    )
    return list(result.scalars().all())


@router.get("/bindings")
async def list_tenant_bindings(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """列出当前租户的模型绑定关系。"""
    result = await db.execute(
        select(TenantModelBinding).where(
            TenantModelBinding.tenant_id == tenant_id,
            TenantModelBinding.enabled == True,
        )
    )
    return list(result.scalars().all())
