"""
租户上下文中间件。

支持两种鉴权方式：
1. X-Tenant-ID 请求头（开发/内部调用）
2. Authorization: Bearer <api_key> 凭证鉴权（外部 API 调用）
"""

import hashlib
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

EXEMPT_PREFIXES: tuple[str, ...] = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
)

TENANT_HEADER = "X-Tenant-ID"


class TenantContextMiddleware(BaseHTTPMiddleware):
    """解析请求中的租户标识并注入到请求状态。"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return await call_next(request)

        tenant_id = self._try_header_auth(request)

        if tenant_id is None:
            tenant_id = await self._try_api_key_auth(request)

        request.state.tenant_id = tenant_id
        return await call_next(request)

    @staticmethod
    def _try_header_auth(request: Request) -> int | None:
        raw = request.headers.get(TENANT_HEADER)
        if raw is None:
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    @staticmethod
    async def _try_api_key_auth(request: Request) -> int | None:
        """通过 Authorization 头中的 API Key 解析租户身份。"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        api_key = auth_header[7:].strip()
        if not api_key:
            return None

        try:
            from sqlalchemy import select
            from app.database import SyncSessionLocal
            from app.models.usage import TenantApiCredential

            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            with SyncSessionLocal() as session:
                cred = session.execute(
                    select(TenantApiCredential).where(
                        TenantApiCredential.secret_hash == key_hash,
                        TenantApiCredential.status == "active",
                    )
                ).scalar_one_or_none()

                if cred is None:
                    return None

                from datetime import datetime, timezone
                cred.last_used_at = datetime.now(timezone.utc)
                session.commit()
                return cred.tenant_id

        except Exception:
            logger.warning("API Key 鉴权异常", exc_info=True)
            return None
