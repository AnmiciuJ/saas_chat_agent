"""
ORM 模型统一导出。

Alembic 迁移与业务层通过此处获取所有模型类与声明基类。
"""

from app.models.base import Base
from app.models.tenant import Plan, Tenant, TenantMembership
from app.models.user import UserAccount
from app.models.model_registry import BaseModel_, EmbeddingModel, TenantModelBinding
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeBaseSnapshot,
    Document,
    DocumentChunk,
    KnowledgeEntry,
    KnowledgeEntryChunk,
    IngestionJob,
)
from app.models.conversation import (
    Conversation,
    ChatMessage,
    ConversationMemoryChunk,
    EndUserProfile,
)
from app.models.usage import UsageEvent, UsageDailyAggregate, TenantApiCredential

__all__ = [
    "Base",
    "Plan",
    "Tenant",
    "TenantMembership",
    "UserAccount",
    "BaseModel_",
    "EmbeddingModel",
    "TenantModelBinding",
    "KnowledgeBase",
    "KnowledgeBaseSnapshot",
    "Document",
    "DocumentChunk",
    "KnowledgeEntry",
    "KnowledgeEntryChunk",
    "IngestionJob",
    "Conversation",
    "ChatMessage",
    "ConversationMemoryChunk",
    "EndUserProfile",
    "UsageEvent",
    "UsageDailyAggregate",
    "TenantApiCredential",
]
