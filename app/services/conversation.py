"""
会话与消息业务逻辑层。
"""

from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.conversation import Conversation, ChatMessage
from app.schemas.conversation import ConversationCreate, ChatMessageCreate


class ConversationService:
    """封装会话创建、消息存取与对话编排调度。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, tenant_id: int, payload: ConversationCreate) -> Conversation:
        conv = Conversation(
            tenant_id=tenant_id,
            knowledge_base_id=payload.knowledge_base_id,
            title=payload.title,
        )
        self._db.add(conv)
        await self._db.flush()
        await self._db.refresh(conv)
        return conv

    async def list_by_tenant(self, tenant_id: int) -> list[Conversation]:
        result = await self._db.execute(
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id)
            .order_by(Conversation.last_message_at.desc().nulls_last())
        )
        return list(result.scalars().all())

    async def list_messages(
        self, tenant_id: int, conv_id: int
    ) -> list[ChatMessage]:
        result = await self._db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.tenant_id == tenant_id,
                ChatMessage.conversation_id == conv_id,
            )
            .order_by(ChatMessage.sequence.asc())
        )
        return list(result.scalars().all())

    async def chat(
        self,
        tenant_id: int,
        conv_id: int,
        payload: ChatMessageCreate,
    ) -> AsyncGenerator[str, None]:
        """
        执行单轮对话编排，返回 SSE 流式生成器。

        流程概要：
        1. 持久化用户消息
        2. 调用在线服务链路（意图识别 -> 检索 -> 重排 -> 推理）
        3. 逐片段返回生成内容并最终持久化助手消息
        """
        # TODO: 接入 online.pipeline 完成完整对话编排
        yield "data: [对话编排尚未接入，此为占位响应]\n\n"
        yield "data: [DONE]\n\n"
