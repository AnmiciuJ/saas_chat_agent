"""
重排序模块。

使用 Cross-Encoder 或其他精排模型对候选片段进行二次排序，
过滤低质量结果并附加引用溯源信息。
"""

from typing import Any


async def rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    对候选片段进行精排并返回排序后的结果。

    当前为直通实现，后续接入 Cross-Encoder 模型。
    """
    # TODO: 接入重排序模型
    return candidates
