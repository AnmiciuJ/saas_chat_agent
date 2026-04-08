"""
全局异常定义与处理器注册。

业务层抛出自定义异常，由此处统一转换为标准化的响应格式。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    """通用业务异常，携带错误码与提示信息。"""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(BusinessError):
    """目标资源不存在。"""

    def __init__(self, message: str = "请求的资源不存在"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class ForbiddenError(BusinessError):
    """操作权限不足。"""

    def __init__(self, message: str = "无权执行此操作"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class QuotaExceededError(BusinessError):
    """用量配额超限。"""

    def __init__(self, message: str = "已超出当前套餐配额"):
        super().__init__(code="QUOTA_EXCEEDED", message=message, status_code=429)


def register_exception_handlers(application: FastAPI) -> None:
    """将自定义异常处理器挂载至应用实例。"""

    @application.exception_handler(BusinessError)
    async def _handle_business_error(request: Request, exc: BusinessError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
