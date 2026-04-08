"""
FastAPI 应用入口。

负责应用实例创建、路由注册、中间件挂载与生命周期管理。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from app.database import async_engine
from app.routers import register_routers
from app.exceptions import register_exception_handlers
from app.middleware.tenant_context import TenantContextMiddleware


@asynccontextmanager
async def lifespan(application: FastAPI):
    """应用生命周期：启动时初始化资源，关闭时释放连接。"""
    yield
    await async_engine.dispose()


def create_app() -> FastAPI:
    """构造并返回 FastAPI 应用实例。"""
    application = FastAPI(
        title="多租户 AI 客服 SaaS",
        version="0.1.0",
        debug=config.DEBUG,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(TenantContextMiddleware)

    register_routers(application)
    register_exception_handlers(application)

    return application


app = create_app()
