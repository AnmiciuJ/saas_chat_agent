"""
模型注册与绑定路由。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_tenant_id

router = APIRouter(prefix="/api/models", tags=["模型管理"])


@router.get("/base")
async def list_base_models(db: AsyncSession = Depends(get_db)):
    """列出平台可用的基座模型。"""
    # TODO: 实现基座模型列表查询
    return []


@router.get("/embedding")
async def list_embedding_models(db: AsyncSession = Depends(get_db)):
    """列出平台可用的嵌入模型。"""
    # TODO: 实现嵌入模型列表查询
    return []


@router.get("/bindings")
async def list_tenant_bindings(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """列出当前租户的模型绑定关系。"""
    # TODO: 实现租户模型绑定查询
    return []
