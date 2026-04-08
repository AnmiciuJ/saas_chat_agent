"""
知识库与文档相关的请求/响应契约。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。"""
    name: str = Field(..., max_length=256)
    description: Optional[str] = None
    embedding_model_key: Optional[str] = None


class KnowledgeBaseOut(BaseModel):
    """知识库信息输出。"""
    id: int
    tenant_id: int
    name: str
    description: Optional[str] = None
    status: str
    embedding_model_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadOut(BaseModel):
    """文档上传结果输出。"""
    id: int
    original_filename: str
    size_bytes: int
    parse_status: str
    index_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeEntryCreate(BaseModel):
    """手工条目创建请求。"""
    title: Optional[str] = Field(None, max_length=512)
    body: str


class KnowledgeEntryOut(BaseModel):
    """手工条目输出。"""
    id: int
    title: Optional[str] = None
    body: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
