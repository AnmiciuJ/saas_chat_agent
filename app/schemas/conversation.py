"""
会话与消息相关的请求/响应契约。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话请求。"""
    knowledge_base_id: Optional[int] = None
    title: Optional[str] = Field(None, max_length=512)
    external_user_key: Optional[str] = None


class ConversationOut(BaseModel):
    """会话信息输出。"""
    id: int
    tenant_id: int
    title: Optional[str] = None
    status: str
    summary: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    """用户发送消息请求。"""
    content: str = Field(..., min_length=1)


class ChatMessageOut(BaseModel):
    """消息输出。"""
    id: int
    conversation_id: int
    sequence: int
    role: str
    content: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    retrieval_refs: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
