"""
流式传输工具函数。

提供 SSE（Server-Sent Events）格式封装，
将原始文本片段转换为符合协议的事件流。
"""

from typing import AsyncGenerator


async def wrap_sse(
    generator: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """将原始文本片段包装为 SSE data 帧。"""
    async for chunk in generator:
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"
