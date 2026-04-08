"""
FastAPI 依赖注入集合。

包含数据库会话获取、当前租户上下文提取等公共依赖。
路由层通过 Depends() 引用，避免重复初始化逻辑。
"""

from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每个请求获取一个独立的数据库会话，请求结束后自动关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_current_tenant_id(request: Request) -> int:
    """
    从请求上下文中提取当前租户标识。

    租户标识由 TenantContextMiddleware 解析后写入 request.state。
    若未携带有效租户信息，拒绝请求。
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少有效的租户身份标识",
        )
    return tenant_id
