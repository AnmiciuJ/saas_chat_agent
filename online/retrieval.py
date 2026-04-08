"""
混合检索：向量召回与关键词召回。

首期实现向量相似度检索（Top-K），Milvus 不可用时降级到关系库全文匹配。
"""

import logging
from typing import Any

import config
from offline.embedding import embed_chunks

logger = logging.getLogger(__name__)

COLLECTION_PREFIX = "kb_vectors"


async def hybrid_retrieve(
    tenant_id: int,
    knowledge_base_id: int | None,
    query: str,
) -> list[dict[str, Any]]:
    """
    执行向量召回，返回候选片段列表。

    每个片段包含 text / score / chunk_index / document_id 等字段。
    """
    if not query or knowledge_base_id is None:
        return []

    candidates = await _vector_retrieve(tenant_id, knowledge_base_id, query)

    if not candidates:
        candidates = _fallback_db_retrieve(tenant_id, knowledge_base_id, query)

    return candidates


async def _vector_retrieve(
    tenant_id: int,
    knowledge_base_id: int,
    query: str,
) -> list[dict[str, Any]]:
    """通过 Milvus 进行向量相似度检索。"""
    try:
        from pymilvus import connections, Collection, utility

        connections.connect(
            alias="default",
            host=config.VECTOR_DB_HOST,
            port=str(config.VECTOR_DB_PORT),
        )

        collection_name = f"{COLLECTION_PREFIX}_{tenant_id}"
        if not utility.has_collection(collection_name):
            return []

        query_vectors = await embed_chunks([query])
        if not query_vectors:
            return []

        collection = Collection(name=collection_name)
        collection.load()

        results = collection.search(
            data=query_vectors,
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=config.RETRIEVAL_TOP_K,
            expr=f"knowledge_base_id == {knowledge_base_id}",
            output_fields=["text", "chunk_index", "document_id"],
        )

        candidates: list[dict[str, Any]] = []
        for hits in results:
            for hit in hits:
                candidates.append({
                    "text": hit.entity.get("text", ""),
                    "score": hit.distance,
                    "chunk_index": hit.entity.get("chunk_index"),
                    "document_id": hit.entity.get("document_id"),
                    "source": "vector",
                })

        logger.info("向量召回 %d 条候选", len(candidates))
        return candidates

    except Exception:
        logger.warning("Milvus 检索不可用，将降级至数据库检索", exc_info=True)
        return []


def _fallback_db_retrieve(
    tenant_id: int,
    knowledge_base_id: int,
    query: str,
) -> list[dict[str, Any]]:
    """Milvus 不可用时，从关系库镜像表做简单文本匹配。"""
    from sqlalchemy import select
    from app.database import SyncSessionLocal
    from app.models.knowledge import DocumentChunk, Document

    candidates: list[dict[str, Any]] = []
    try:
        with SyncSessionLocal() as session:
            stmt = (
                select(DocumentChunk)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.tenant_id == tenant_id,
                    Document.knowledge_base_id == knowledge_base_id,
                    DocumentChunk.text_content.contains(query[:50]),
                )
                .limit(config.RETRIEVAL_TOP_K)
            )
            rows = session.execute(stmt).scalars().all()
            for row in rows:
                candidates.append({
                    "text": row.text_content,
                    "score": 0.5,
                    "chunk_index": row.chunk_index,
                    "document_id": row.document_id,
                    "source": "db_fallback",
                })
    except Exception:
        logger.warning("数据库降级检索也失败", exc_info=True)

    return candidates
