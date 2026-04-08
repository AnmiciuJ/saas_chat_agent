"""
离线入库总调度。

串联解析、分块、向量化与索引写入四个阶段，
以文档为粒度执行完整的离线处理流水线。
"""

from offline.parsing import parse_document
from offline.chunking import chunk_text
from offline.embedding import embed_chunks
from offline.indexing import write_to_index


async def run_ingestion_pipeline(
    tenant_id: int,
    document_id: int,
) -> None:
    """
    对指定文档执行全流程离线处理。

    各阶段异常将上抛至调用方（通常为异步任务），
    由任务层负责状态更新与重试。
    """
    raw_text = await parse_document(tenant_id, document_id)

    chunks = chunk_text(raw_text)

    vectors = await embed_chunks(chunks)

    await write_to_index(
        tenant_id=tenant_id,
        document_id=document_id,
        chunks=chunks,
        vectors=vectors,
    )
