"""
路由注册中心。

将各业务域的路由器统一挂载至 FastAPI 应用实例。
"""

from fastapi import FastAPI

from app.routers.tenant import router as tenant_router
from app.routers.knowledge import router as knowledge_router
from app.routers.conversation import router as conversation_router
from app.routers.model_registry import router as model_registry_router


def register_routers(application: FastAPI) -> None:
    """将全部业务路由注册至应用。"""
    application.include_router(tenant_router)
    application.include_router(knowledge_router)
    application.include_router(conversation_router)
    application.include_router(model_registry_router)
