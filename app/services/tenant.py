"""
租户业务逻辑层。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    """封装租户相关的业务规则与数据操作。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, payload: TenantCreate) -> Tenant:
        tenant = Tenant(
            name=payload.name,
            slug=payload.slug,
            contact_email=payload.contact_email,
            plan_id=payload.plan_id,
            status="pending_review",
        )
        self._db.add(tenant)
        await self._db.flush()
        await self._db.refresh(tenant)
        return tenant

    async def get_by_id(self, tenant_id: int) -> Tenant:
        result = await self._db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise NotFoundError("租户不存在")
        return tenant

    async def update(self, tenant_id: int, payload: TenantUpdate) -> Tenant:
        tenant = await self.get_by_id(tenant_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        await self._db.flush()
        await self._db.refresh(tenant)
        return tenant
