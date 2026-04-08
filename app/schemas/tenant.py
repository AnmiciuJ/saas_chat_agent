"""
租户与套餐相关的请求/响应契约。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class PlanOut(BaseModel):
    """套餐信息输出。"""
    id: int
    code: str
    name: str
    description: Optional[str] = None
    max_knowledge_bases: int
    max_documents_total: int
    max_storage_bytes: int
    max_monthly_chat_turns: int
    max_monthly_tokens: int
    features: Optional[dict] = None
    is_active: bool

    model_config = {"from_attributes": True}


class TenantCreate(BaseModel):
    """租户注册请求。"""
    name: str = Field(..., max_length=256)
    slug: str = Field(..., max_length=64, pattern=r"^[a-z0-9\-]+$")
    contact_email: EmailStr
    plan_id: Optional[int] = None


class TenantOut(BaseModel):
    """租户信息输出。"""
    id: int
    name: str
    slug: str
    status: str
    contact_email: str
    plan_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    """租户信息更新（部分字段可选）。"""
    name: Optional[str] = Field(None, max_length=256)
    contact_email: Optional[EmailStr] = None
    plan_id: Optional[int] = None
