"""
通用响应与分页契约。

所有接口统一使用此处定义的响应包装与分页参数。
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """分页查询参数。"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class PagedResponse(BaseModel, Generic[T]):
    """分页响应包装。"""
    items: list[T]
    total: int
    page: int
    page_size: int


class SuccessResponse(BaseModel):
    """无业务载荷的操作成功响应。"""
    ok: bool = True
    message: str = "操作成功"
