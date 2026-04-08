"""
会话与消息路由。
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_tenant_id
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    ChatMessageCreate,
    ChatMessageOut,
)
from app.services.conversation import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["会话管理"])


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话。"""
    service = ConversationService(db)
    return await service.create(tenant_id, payload)


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """列出当前租户的全部会话。"""
    service = ConversationService(db)
    return await service.list_by_tenant(tenant_id)


@router.get("/{conv_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    conv_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取指定会话的消息列表。"""
    service = ConversationService(db)
    return await service.list_messages(tenant_id, conv_id)


@router.post("/{conv_id}/messages", status_code=200)
async def send_message(
    conv_id: int,
    payload: ChatMessageCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    发送用户消息并获取助手回复。

    返回 SSE 流式响应，逐片段推送生成内容。
    """
    service = ConversationService(db)
    generator = service.chat(tenant_id, conv_id, payload)
    return StreamingResponse(generator, media_type="text/event-stream")
