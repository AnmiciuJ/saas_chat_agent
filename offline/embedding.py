"""
向量化模块。

调用嵌入模型服务将文本块批量转换为向量表示。
"""

import config


async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    将文本块列表转换为对应的向量列表。

    按配置的批大小分批调用嵌入服务，避免单次请求过大。
    """
    # TODO: 对接嵌入模型 API（如 OpenAI Embeddings / 本地模型）
    batch_size = config.INGEST_EMBED_BATCH_SIZE
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        # 占位：每个块生成零向量
        vectors.extend([[0.0] * 768] * len(batch))
    return vectors
