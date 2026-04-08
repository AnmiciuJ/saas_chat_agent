"""
重排序模块。

首期按向量相似度分数截断低质量结果，预留 Cross-Encoder 精排接口。
"""

from typing import Any

SCORE_THRESHOLD = 0.3


async def rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    threshold: float = SCORE_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    对候选片段进行排序与过滤。

    首期策略：按 score 降序排列，过滤低于阈值的片段。
    后续可替换为 Cross-Encoder 模型精排。
    """
    if not candidates:
        return []

    sorted_candidates = sorted(
        candidates, key=lambda x: x.get("score", 0), reverse=True
    )

    filtered = [c for c in sorted_candidates if c.get("score", 0) >= threshold]

    return filtered
