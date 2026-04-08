"""
租户管理路由。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.tenant import TenantCreate, TenantOut, TenantUpdate
from app.schemas.common import SuccessResponse
from app.services.tenant import TenantService

router = APIRouter(prefix="/api/tenants", tags=["租户管理"])


@router.post("", response_model=TenantOut, status_code=201)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    """注册新租户。"""
    service = TenantService(db)
    return await service.create(payload)


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取租户详情。"""
    service = TenantService(db)
    return await service.get_by_id(tenant_id)


@router.patch("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新租户信息。"""
    service = TenantService(db)
    return await service.update(tenant_id, payload)
