"""
基座模型目录、嵌入模型目录与租户模型绑定。
"""

from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BaseModel_(Base, TimestampMixin):
    """平台可接入的大语言推理模型目录。

    命名后缀加下划线以避免与 Python 内建冲突。
    """

    __tablename__ = "base_model"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    max_context_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supports_streaming: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    bindings: Mapped[list["TenantModelBinding"]] = relationship(back_populates="base_model")

    __table_args__ = (
        UniqueConstraint("provider", "model_key", name="uq_base_model_provider_key"),
    )


class EmbeddingModel(Base, TimestampMixin):
    """嵌入模型目录，与知识库向量化过程关联。"""

    __tablename__ = "embedding_model"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    vector_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "model_key", name="uq_embedding_model_provider_key"),
    )


class TenantModelBinding(Base, TimestampMixin):
    """租户与基座模型的绑定关系，含默认策略与优先级。"""

    __tablename__ = "tenant_model_binding"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id"), nullable=False
    )
    base_model_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("base_model.id"), nullable=False
    )
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    base_model: Mapped["BaseModel_"] = relationship(back_populates="bindings")
