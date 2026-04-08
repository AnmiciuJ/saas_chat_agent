"""
会话摘要异步任务。

在消息积累到一定轮次后，调用大模型生成摘要并回写会话记录，
压缩短期记忆避免上下文窗口溢出。
"""

import asyncio
import logging

from sqlalchemy import select

from app.database import SyncSessionLocal
from app.models.conversation import Conversation, ChatMessage
from workers.celery_app import celery

logger = logging.getLogger(__name__)

SUMMARIZE_THRESHOLD = 20


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_conversation_summary(
    self, tenant_id: int, conversation_id: int
) -> dict:
    """为指定会话生成摘要并回写数据库。"""
    try:
        asyncio.run(
            _do_summarize(tenant_id, conversation_id)
        )
        return {"status": "succeeded", "conversation_id": conversation_id}
    except Exception as exc:
        logger.exception("会话摘要任务异常: conversation_id=%s", conversation_id)
        raise self.retry(exc=exc)


async def _do_summarize(tenant_id: int, conversation_id: int) -> None:
    """读取消息、调用大模型生成摘要、更新数据库。"""
    messages = _load_messages(tenant_id, conversation_id)
    if len(messages) < SUMMARIZE_THRESHOLD:
        logger.info(
            "消息不足 %d 轮，跳过摘要: conversation_id=%s",
            SUMMARIZE_THRESHOLD, conversation_id,
        )
        return

    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages
    )

    from online.llm_client import complete

    prompt = (
        "请将以下对话内容压缩为一段简洁的摘要，保留关键信息和用户意图，"
        "不超过 300 字：\n\n" + conversation_text
    )
    context = {"system_prompt": "", "history": []}
    summary_text, _, _ = await complete(context, prompt)

    _save_summary(conversation_id, summary_text)
    logger.info("会话摘要已更新: conversation_id=%s", conversation_id)


def _load_messages(
    tenant_id: int, conversation_id: int
) -> list[dict[str, str]]:
    with SyncSessionLocal() as session:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.tenant_id == tenant_id,
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.role.in_(["user", "assistant"]),
            )
            .order_by(ChatMessage.sequence.asc())
        )
        rows = session.execute(stmt).scalars().all()
    return [{"role": r.role, "content": r.content} for r in rows]


def _save_summary(conversation_id: int, summary: str) -> None:
    with SyncSessionLocal() as session:
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one()
        conv.summary = summary
        session.commit()
