"""
会话记忆组装。

将短期上下文（最近消息 + 摘要）与检索结果合并为上下文包，
供大模型推理使用。长期记忆与用户画像在 Phase 4 补全。
"""

import logging
from typing import Any

from sqlalchemy import select

from app.database import SyncSessionLocal
from app.models.conversation import Conversation, ChatMessage
from app.services.session_memory import get_window

logger = logging.getLogger(__name__)

DB_FALLBACK_WINDOW = 10


async def assemble_context(
    tenant_id: int,
    conversation_id: int,
    retrieval_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    组装完整的上下文包。

    优先从 Redis 短期窗口读取历史，不可用时降级到关系库。
    """
    history = _load_from_redis(tenant_id, conversation_id)
    if not history:
        history = _load_from_db(tenant_id, conversation_id)

    summary = _load_summary(conversation_id)

    system_prompt = "你是一个专业的 AI 客服助手，请根据提供的知识库内容准确回答用户的问题。"
    if summary:
        system_prompt += f"\n\n以下是本次会话的历史摘要：{summary}"

    return {
        "system_prompt": system_prompt,
        "history": history,
        "retrieval_context": retrieval_results,
    }


def _load_from_redis(
    tenant_id: int, conversation_id: int
) -> list[dict[str, str]]:
    """从 Redis 短期窗口读取最近消息。"""
    try:
        return get_window(tenant_id, conversation_id)
    except Exception:
        logger.warning("Redis 短期窗口读取失败，将降级到数据库", exc_info=True)
        return []


def _load_from_db(
    tenant_id: int, conversation_id: int
) -> list[dict[str, str]]:
    """降级：从关系库读取最近消息。"""
    with SyncSessionLocal() as session:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.tenant_id == tenant_id,
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.role.in_(["user", "assistant"]),
            )
            .order_by(ChatMessage.sequence.desc())
            .limit(DB_FALLBACK_WINDOW)
        )
        rows = session.execute(stmt).scalars().all()

    return [
        {"role": row.role, "content": row.content}
        for row in reversed(rows)
    ]


def _load_summary(conversation_id: int) -> str | None:
    """读取会话摘要。"""
    with SyncSessionLocal() as session:
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()
        return conv.summary if conv else None
