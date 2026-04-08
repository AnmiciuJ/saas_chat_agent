"""
向量索引写入模块。

将向量化结果写入 Milvus 并回写关系库中的块镜像记录。
开发阶段若 Milvus 不可用则仅写关系库镜像。
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SyncSessionLocal
from app.models.knowledge import DocumentChunk, Document

logger = logging.getLogger(__name__)

COLLECTION_PREFIX = "kb_vectors"


def write_to_index(
    tenant_id: int,
    document_id: int,
    knowledge_base_id: int,
    chunks: list[str],
    vectors: list[list[float]],
) -> None:
    """
    将块文本与对应向量写入 Milvus，并同步关系库镜像。

    当 Milvus 不可用时，仅写入关系库镜像表以保证数据不丢失。
    """
    vector_point_ids = _try_write_milvus(
        tenant_id, knowledge_base_id, document_id, chunks, vectors
    )

    _write_chunk_mirror(tenant_id, document_id, chunks, vector_point_ids)


def _try_write_milvus(
    tenant_id: int,
    knowledge_base_id: int,
    document_id: int,
    chunks: list[str],
    vectors: list[list[float]],
) -> list[str | None]:
    """尝试写入 Milvus，失败时返回空标识列表。"""
    point_ids = [str(uuid.uuid4()) for _ in chunks]

    try:
        from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
        import config

        connections.connect(
            alias="default",
            host=config.VECTOR_DB_HOST,
            port=str(config.VECTOR_DB_PORT),
        )

        collection_name = f"{COLLECTION_PREFIX}_{tenant_id}"
        dim = len(vectors[0]) if vectors else 1024

        if not utility.has_collection(collection_name):
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name="tenant_id", dtype=DataType.INT64),
                FieldSchema(name="knowledge_base_id", dtype=DataType.INT64),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="chunk_index", dtype=DataType.INT32),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
            ]
            schema = CollectionSchema(fields=fields)
            Collection(name=collection_name, schema=schema)
            logger.info("Milvus 集合已创建: %s", collection_name)

        collection = Collection(name=collection_name)
        collection.insert([
            point_ids,
            [tenant_id] * len(chunks),
            [knowledge_base_id] * len(chunks),
            [document_id] * len(chunks),
            list(range(len(chunks))),
            [c[:8000] for c in chunks],
            vectors,
        ])
        collection.flush()

        index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 256}}
        if not collection.has_index():
            collection.create_index(field_name="vector", index_params=index_params)

        logger.info("Milvus 写入完成: %d 条向量", len(chunks))
        return point_ids

    except Exception:
        logger.warning("Milvus 不可用，仅写入关系库镜像", exc_info=True)
        return [None] * len(chunks)


def _write_chunk_mirror(
    tenant_id: int,
    document_id: int,
    chunks: list[str],
    vector_point_ids: list[str | None],
) -> None:
    """批量写入文档块镜像表。"""
    import config

    provider = config.EMBEDDING_PROVIDERS[config.EMBEDDING_DEFAULT_PROVIDER]
    embedding_model_key = provider["default_model"]

    with SyncSessionLocal() as session:
        for idx, (text, point_id) in enumerate(zip(chunks, vector_point_ids)):
            chunk = DocumentChunk(
                tenant_id=tenant_id,
                document_id=document_id,
                chunk_index=idx,
                text_content=text,
                char_count=len(text),
                vector_point_id=point_id,
                embedding_model_key=embedding_model_key,
            )
            session.add(chunk)
        session.commit()
        logger.info("块镜像写入完成: document_id=%s, %d 块", document_id, len(chunks))
