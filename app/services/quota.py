"""
套餐配额校验。

在关键操作前检查租户是否超出当前套餐限额。
"""

from datetime import date

from sqlalchemy import select, func

from app.database import SyncSessionLocal
from app.models.tenant import Tenant, Plan
from app.models.knowledge import KnowledgeBase, Document
from app.models.usage import UsageDailyAggregate
from app.exceptions import QuotaExceededError


def check_chat_quota(tenant_id: int) -> None:
    """检查本月对话轮次是否超限。"""
    plan = _get_tenant_plan(tenant_id)
    if plan is None or plan.max_monthly_chat_turns == -1:
        return

    monthly_turns = _get_monthly_chat_turns(tenant_id)
    if monthly_turns >= plan.max_monthly_chat_turns:
        raise QuotaExceededError("本月对话轮次已达套餐上限")


def check_knowledge_base_quota(tenant_id: int) -> None:
    """检查知识库数量是否超限。"""
    plan = _get_tenant_plan(tenant_id)
    if plan is None or plan.max_knowledge_bases == -1:
        return

    with SyncSessionLocal() as session:
        count = session.execute(
            select(func.count()).select_from(KnowledgeBase).where(
                KnowledgeBase.tenant_id == tenant_id
            )
        ).scalar()

    if count >= plan.max_knowledge_bases:
        raise QuotaExceededError("知识库数量已达套餐上限")


def check_storage_quota(tenant_id: int) -> None:
    """检查存储容量是否超限。"""
    plan = _get_tenant_plan(tenant_id)
    if plan is None or plan.max_storage_bytes == -1:
        return

    with SyncSessionLocal() as session:
        total_bytes = session.execute(
            select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
                Document.tenant_id == tenant_id
            )
        ).scalar()

    if total_bytes >= plan.max_storage_bytes:
        raise QuotaExceededError("知识库存储容量已达套餐上限")


def _get_tenant_plan(tenant_id: int) -> Plan | None:
    with SyncSessionLocal() as session:
        tenant = session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        ).scalar_one_or_none()
        if tenant is None or tenant.plan_id is None:
            return None
        plan = session.execute(
            select(Plan).where(Plan.id == tenant.plan_id)
        ).scalar_one_or_none()
        return plan


def _get_monthly_chat_turns(tenant_id: int) -> int:
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

    with SyncSessionLocal() as session:
        total = session.execute(
            select(func.coalesce(func.sum(UsageDailyAggregate.chat_turns), 0)).where(
                UsageDailyAggregate.tenant_id == tenant_id,
                UsageDailyAggregate.bucket_date >= first_of_month,
            )
        ).scalar()
    return int(total)
