"""
大模型推理客户端。

统一封装对自部署模型与第三方推理服务的调用，
支持流式与非流式两种响应模式。
"""

from typing import Any, AsyncGenerator

import httpx

import config


async def stream_completion(
    context: dict[str, Any],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    向推理服务发送流式请求，逐片段产出生成文本。

    当前为占位实现，后续对接实际模型网关。
    """
    # TODO: 拼装 prompt，调用 LLM API 获取流式响应
    yield "[占位] 推理服务尚未对接"


async def complete(
    context: dict[str, Any],
    user_message: str,
) -> str:
    """非流式推理调用，返回完整回复文本。"""
    # TODO: 实现非流式调用
    return "[占位] 推理服务尚未对接"
