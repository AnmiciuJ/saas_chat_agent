"""
知识库、文档、文本块、手工条目与入库任务模型。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Enum, ForeignKey, Integer, String, Text, JSON,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    """租户私有知识库，绑定特定嵌入模型用于向量化。"""

    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="kb_status"),
        nullable=False,
        default="active",
    )
    embedding_model_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("embedding_model.id"), nullable=True
    )
    embedding_model_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    current_snapshot_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="knowledge_base")
    entries: Mapped[list["KnowledgeEntry"]] = relationship(back_populates="knowledge_base")
    snapshots: Mapped[list["KnowledgeBaseSnapshot"]] = relationship(back_populates="knowledge_base")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_kb_tenant_name"),
    )


class KnowledgeBaseSnapshot(Base):
    """知识库版本快照，用于回滚与审计。"""

    __tablename__ = "knowledge_base_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_base.id"), nullable=False
    )
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="snapshots")


class Document(Base, TimestampMixin):
    """上传的原始文件元数据。"""

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_base.id"), nullable=False
    )
    snapshot_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    source_type: Mapped[str] = mapped_column(
        Enum("file_upload", "url_import", "api_push", name="doc_source_type"),
        nullable=False,
        default="file_upload",
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    content_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parse_status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "ready", "failed", name="parse_status"),
        nullable=False,
        default="pending",
    )
    index_status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "ready", "failed", name="index_status"),
        nullable=False,
        default="pending",
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_profile_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extracted_aux_storage_key: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    """文档经语义分块后的文本块镜像，与向量库点位一一对应。"""

    __tablename__ = "document_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vector_point_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_model_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    snapshot_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunk_idx"),
    )


class KnowledgeEntry(Base, TimestampMixin):
    """手工录入的知识条目，与文件型知识并列。"""

    __tablename__ = "knowledge_entry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_base.id"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "published", "archived", name="entry_status"),
        nullable=False,
        default="draft",
    )
    snapshot_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="entries")
    chunks: Mapped[list["KnowledgeEntryChunk"]] = relationship(back_populates="entry")


class KnowledgeEntryChunk(Base):
    """手工条目分块，与向量库点位一一对应。"""

    __tablename__ = "knowledge_entry_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    knowledge_entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_entry.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vector_point_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_model_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    snapshot_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    entry: Mapped["KnowledgeEntry"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint(
            "knowledge_entry_id", "chunk_index", name="uq_entry_chunk_idx"
        ),
    )


class IngestionJob(Base, TimestampMixin):
    """离线解析与索引构建任务的进度追踪。"""

    __tablename__ = "ingestion_job"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document.id"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(
        Enum(
            "parse", "chunk", "embed", "index", "full_pipeline",
            name="ingestion_job_type",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "queued", "running", "succeeded", "failed", "cancelled",
            name="ingestion_job_status",
        ),
        nullable=False,
        default="queued",
    )
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    worker_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
