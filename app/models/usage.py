"""
用量事件、日汇总与租户接入凭证模型。
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Date, Enum, ForeignKey, Integer, Numeric, String, JSON,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UsageEvent(Base):
    """原始用量事件，由业务链路实时写入，后台异步汇总。"""

    __tablename__ = "usage_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        Enum(
            "chat_turn", "prompt_tokens", "completion_tokens",
            "storage_bytes", "api_call",
            name="usage_event_type",
        ),
        nullable=False,
    )
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class UsageDailyAggregate(Base):
    """按日汇总的用量指标，用于配额校验与报表展示。"""

    __tablename__ = "usage_daily_aggregate"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False)
    chat_turns: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "bucket_date", name="uq_usage_daily_tenant_date"),
    )


class TenantApiCredential(Base, TimestampMixin):
    """租户接入凭证：用于第三方系统通过密钥调用开放接口。"""

    __tablename__ = "tenant_api_credential"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "revoked", name="credential_status"),
        nullable=False,
        default="active",
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
