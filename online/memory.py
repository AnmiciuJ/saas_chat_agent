"""
会话记忆组装。

负责将短期上下文（滑动窗口 + 摘要）、长期记忆（向量检索）、
结构化画像（偏好标签）合并为最终上下文包，供大模型推理使用。
"""

from typing import Any


async def assemble_context(
    tenant_id: int,
    conversation_id: int,
    retrieval_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    组装完整的上下文包。

    返回:
        包含 system_prompt / history / retrieval_context / user_profile 的字典
    """
    # TODO: 读取 Redis 短期窗口
    # TODO: 检索长期记忆向量
    # TODO: 加载用户画像
    return {
        "system_prompt": "",
        "history": [],
        "retrieval_context": retrieval_results,
        "user_profile": {},
    }
