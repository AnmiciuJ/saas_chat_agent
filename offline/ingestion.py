"""
离线入库总调度。

串联解析、分块、向量化与索引写入四个阶段，
以文档为粒度执行完整的离线处理流水线。
同步更新入库任务与文档的状态。
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SyncSessionLocal
from app.models.knowledge import Document, IngestionJob
from offline.parsing import parse_document
from offline.chunking import chunk_text
from offline.embedding import embed_chunks
from offline.indexing import write_to_index

logger = logging.getLogger(__name__)


def _load_document_info(document_id: int) -> dict:
    """从关系库读取文档元数据，供各阶段使用。"""
    with SyncSessionLocal() as session:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one()
        return {
            "storage_key": doc.storage_key,
            "mime_type": doc.mime_type,
            "knowledge_base_id": doc.knowledge_base_id,
        }


def _update_status(
    document_id: int,
    parse_status: str | None = None,
    index_status: str | None = None,
    error: str | None = None,
) -> None:
    """更新文档的解析/索引状态。"""
    with SyncSessionLocal() as session:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one()
        if parse_status:
            doc.parse_status = parse_status
        if index_status:
            doc.index_status = index_status
        if error:
            doc.last_error = error
        session.commit()


def _update_job_status(
    document_id: int,
    status: str,
    error_detail: str | None = None,
) -> None:
    """更新入库任务的状态。"""
    with SyncSessionLocal() as session:
        job = session.execute(
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.id.desc())
        ).scalar_one_or_none()
        if job is None:
            return
        job.status = status
        now = datetime.now(timezone.utc)
        if status == "running":
            job.started_at = now
        elif status in ("succeeded", "failed"):
            job.finished_at = now
        if error_detail:
            job.error_detail = error_detail
        session.commit()


async def run_ingestion_pipeline(
    tenant_id: int,
    document_id: int,
) -> None:
    """
    对指定文档执行全流程离线处理。

    阶段顺序：解析 -> 分块 -> 向量化 -> 索引写入。
    每个阶段前后更新状态，异常时标记失败并上抛。
    """
    doc_info = _load_document_info(document_id)
    _update_job_status(document_id, "running")

    try:
        _update_status(document_id, parse_status="processing")
        raw_text = await parse_document(
            tenant_id=tenant_id,
            document_id=document_id,
            storage_key=doc_info["storage_key"],
            mime_type=doc_info["mime_type"],
        )
        _update_status(document_id, parse_status="ready")

        chunks = chunk_text(raw_text)
        if not chunks:
            _update_status(document_id, index_status="ready")
            _update_job_status(document_id, "succeeded")
            logger.info("文档无可用文本块: document_id=%s", document_id)
            return

        _update_status(document_id, index_status="processing")
        vectors = await embed_chunks(chunks)

        write_to_index(
            tenant_id=tenant_id,
            document_id=document_id,
            knowledge_base_id=doc_info["knowledge_base_id"],
            chunks=chunks,
            vectors=vectors,
        )

        _update_status(document_id, index_status="ready")
        _update_job_status(document_id, "succeeded")
        logger.info("文档入库完成: document_id=%s, %d 块", document_id, len(chunks))

    except Exception as exc:
        error_msg = str(exc)[:2000]
        _update_status(
            document_id,
            parse_status="failed",
            index_status="failed",
            error=error_msg,
        )
        _update_job_status(document_id, "failed", error_detail=error_msg)
        raise
