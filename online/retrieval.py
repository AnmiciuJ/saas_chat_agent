"""
混合检索：向量召回与关键词召回。

将向量相似度检索（Top-K）与 BM25 关键词检索的结果合并，
输出候选文本片段列表供重排序环节使用。
"""

from typing import Any


async def hybrid_retrieve(
    tenant_id: int,
    knowledge_base_id: int | None,
    query: str,
) -> list[dict[str, Any]]:
    """
    执行向量召回与关键词召回，返回合并后的候选片段。

    每个候选片段为字典，包含 text / score / source 等字段。
    """
    # TODO: 对接向量数据库执行 Top-K 召回
    # TODO: 对接 BM25 关键词检索
    return []
