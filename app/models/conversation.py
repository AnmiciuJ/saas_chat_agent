"""
会话、消息、长期记忆块与终端用户画像模型。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Enum, ForeignKey, Integer, String, Text, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EndUserProfile(Base, TimestampMixin):
    """终端用户画像：跨会话偏好与结构化标签。"""

    __tablename__ = "end_user_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    external_user_key: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    preference_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tag_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="end_user_profile"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "external_user_key", name="uq_profile_tenant_user"
        ),
    )


class Conversation(Base, TimestampMixin):
    """对话会话：承载消息序列与短期记忆摘要。"""

    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    knowledge_base_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("knowledge_base.id"), nullable=True
    )
    user_account_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("user_account.id"), nullable=True
    )
    end_user_profile_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("end_user_profile.id"), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("open", "closed", name="conversation_status"),
        nullable=False,
        default="open",
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    end_user_profile: Mapped[Optional["EndUserProfile"]] = relationship(
        back_populates="conversations"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="conversation")
    memory_chunks: Mapped[list["ConversationMemoryChunk"]] = relationship(
        back_populates="conversation"
    )


class ChatMessage(Base):
    """单条对话消息：记录角色、内容、推理链路摘要与用量指标。"""

    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversation.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system", "tool", name="message_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    used_base_model_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    rewritten_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pipeline_trace: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retrieval_refs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default="CURRENT_TIMESTAMP", nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence", name="uq_msg_conv_seq"
        ),
    )


class ConversationMemoryChunk(Base):
    """长期记忆：历史对话片段向量化后的关系库镜像。"""

    __tablename__ = "conversation_memory_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversation.id"), nullable=False
    )
    source_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chat_message.id"), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_point_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_model_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default="CURRENT_TIMESTAMP", nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="memory_chunks")
