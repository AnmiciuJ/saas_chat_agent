"""
语义分块模块。

将解析后的长文本按照配置策略拆分为适合向量化的短文本块。
支持按段落、滑动窗口与递归拆分等模式。
"""

import config


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """
    将输入文本拆分为块列表。

    参数:
        text: 待分块的完整文本
        chunk_size: 每块目标字符数，默认取全局配置
        chunk_overlap: 块间重叠字符数，默认取全局配置

    返回:
        分块后的文本列表
    """
    size = chunk_size or config.INGEST_CHUNK_SIZE
    overlap = chunk_overlap or config.INGEST_CHUNK_OVERLAP

    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
    return chunks
