"""
会话与消息业务逻辑层。
"""

import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SyncSessionLocal
from app.exceptions import NotFoundError
from app.models.conversation import Conversation, ChatMessage
from app.schemas.conversation import ConversationCreate, ChatMessageCreate
from app.services.session_memory import push_message
from app.services.usage import record_chat_usage

logger = logging.getLogger(__name__)


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
        执行单轮对话：持久化用户消息 -> 调用在线链路 -> 流式返回 -> 持久化助手消息。
        """
        conv = await self._db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.tenant_id == tenant_id,
            )
        )
        conversation = conv.scalar_one_or_none()
        if conversation is None:
            raise NotFoundError("会话不存在")

        next_seq = await self._next_sequence(conv_id)

        user_msg = ChatMessage(
            tenant_id=tenant_id,
            conversation_id=conv_id,
            sequence=next_seq,
            role="user",
            content=payload.content,
        )
        self._db.add(user_msg)
        conversation.last_message_at = datetime.now(timezone.utc)
        await self._db.flush()
        await self._db.commit()

        try:
            push_message(tenant_id, conv_id, "user", payload.content)
        except Exception:
            logger.warning("Redis 写入用户消息失败", exc_info=True)

        from online.pipeline import run_chat_pipeline

        full_response: list[str] = []

        async for chunk in run_chat_pipeline(
            tenant_id=tenant_id,
            conversation_id=conv_id,
            user_message=payload.content,
            knowledge_base_id=conversation.knowledge_base_id,
        ):
            full_response.append(chunk)
            yield f"data: {chunk}\n\n"

        yield "data: [DONE]\n\n"

        assistant_text = "".join(full_response)
        self._save_assistant_message_sync(
            tenant_id=tenant_id,
            conv_id=conv_id,
            sequence=next_seq + 1,
            content=assistant_text,
        )

        try:
            record_chat_usage(
                tenant_id=tenant_id,
                conversation_id=conv_id,
                prompt_tokens=0,
                completion_tokens=0,
            )
        except Exception:
            logger.warning("用量记录失败", exc_info=True)

    async def _next_sequence(self, conv_id: int) -> int:
        result = await self._db.execute(
            select(func.coalesce(func.max(ChatMessage.sequence), 0)).where(
                ChatMessage.conversation_id == conv_id
            )
        )
        return result.scalar() + 1

    @staticmethod
    def _save_assistant_message_sync(
        tenant_id: int,
        conv_id: int,
        sequence: int,
        content: str,
    ) -> None:
        """流式结束后同步写入助手消息（此时异步会话已释放）。"""
        with SyncSessionLocal() as session:
            msg = ChatMessage(
                tenant_id=tenant_id,
                conversation_id=conv_id,
                sequence=sequence,
                role="assistant",
                content=content,
            )
            session.add(msg)
            session.commit()

        try:
            push_message(tenant_id, conv_id, "assistant", content)
        except Exception:
            logger.warning("Redis 写入助手消息失败", exc_info=True)
