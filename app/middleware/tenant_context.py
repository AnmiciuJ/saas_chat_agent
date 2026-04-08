"""
租户上下文中间件。

从请求头中提取租户标识，写入 request.state 供下游依赖使用。
当请求路径属于免鉴权白名单时跳过解析。
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

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

        raw_tenant_id = request.headers.get(TENANT_HEADER)
        if raw_tenant_id is not None:
            try:
                request.state.tenant_id = int(raw_tenant_id)
            except (ValueError, TypeError):
                request.state.tenant_id = None
        else:
            request.state.tenant_id = None

        return await call_next(request)
