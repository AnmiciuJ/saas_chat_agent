"""
向量化模块。

调用嵌入模型服务将文本块批量转换为向量表示。
对接 DashScope 兼容接口。
"""

import logging

import httpx

import config

logger = logging.getLogger(__name__)


async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    将文本块列表转换为对应的向量列表。

    按配置的批大小分批调用嵌入服务。
    """
    if not chunks:
        return []

    provider_key = config.EMBEDDING_DEFAULT_PROVIDER
    provider = config.EMBEDDING_PROVIDERS[provider_key]
    batch_size = config.INGEST_EMBED_BATCH_SIZE
    vectors: list[list[float]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_vectors = await _call_embedding_api(client, provider, batch)
            vectors.extend(batch_vectors)

    return vectors


async def _call_embedding_api(
    client: httpx.AsyncClient,
    provider: dict,
    texts: list[str],
) -> list[list[float]]:
    """调用嵌入模型 API 并返回向量列表。"""
    response = await client.post(
        provider["api_base_url"],
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": provider["default_model"],
            "input": texts,
            "encoding_format": "float",
        },
    )
    response.raise_for_status()
    data = response.json()

    sorted_items = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_items]
