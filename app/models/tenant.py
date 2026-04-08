"""
套餐、租户与租户成员模型。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    """套餐定义：约束各租户的资源配额与功能边界。"""

    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_knowledge_bases: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    max_documents_total: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    max_storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=-1)
    max_monthly_chat_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    max_monthly_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=-1)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    tenants: Mapped[list["Tenant"]] = relationship(back_populates="plan")


class Tenant(Base, TimestampMixin):
    """租户实体：系统数据隔离的最小归属单元。"""

    __tablename__ = "tenant"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending_review", "active", "suspended", "archived", name="tenant_status"),
        nullable=False,
        default="pending_review",
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("plan.id"), nullable=True
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    plan: Mapped[Optional["Plan"]] = relationship(back_populates="tenants")
    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="tenant")


class TenantMembership(Base):
    """用户在某租户下的成员关系与角色绑定。"""

    __tablename__ = "tenant_membership"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id"), nullable=False
    )
    user_account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_account.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        Enum("owner", "admin", "member", "viewer", name="membership_role"),
        nullable=False,
        default="member",
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default="CURRENT_TIMESTAMP", nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    user: Mapped["UserAccount"] = relationship(back_populates="memberships")

    __table_args__ = (
        {"mysql_charset": "utf8mb4"},
    )
