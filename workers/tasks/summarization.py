"""
会话摘要异步任务。

定期或在会话关闭时，将近期对话内容压缩为摘要，
更新至会话记录以支撑短期记忆机制。
"""

import asyncio
import logging

from workers.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_conversation_summary(
    self, tenant_id: int, conversation_id: int
) -> dict:
    """
    为指定会话生成摘要并回写数据库。
    """
    try:
        # TODO: 读取近期消息，调用大模型生成摘要，更新 conversation.summary
        return {"status": "succeeded", "conversation_id": conversation_id}
    except Exception as exc:
        logger.exception("会话摘要任务异常: conversation_id=%s", conversation_id)
        raise self.retry(exc=exc)
