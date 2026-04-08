"""
知识库离线处理异步任务。

由文档上传接口或管理后台触发，执行文档解析到索引写入的全流程。
"""

import asyncio
import logging

from workers.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def run_document_ingestion(self, tenant_id: int, document_id: int) -> dict:
    """
    文档全流程入库任务。

    失败时自动重试，重试次数与间隔由装饰器参数控制。
    """
    try:
        from offline.ingestion import run_ingestion_pipeline

        asyncio.run(run_ingestion_pipeline(tenant_id, document_id))
        return {"status": "succeeded", "document_id": document_id}
    except Exception as exc:
        logger.exception("文档入库任务异常: document_id=%s", document_id)
        raise self.retry(exc=exc)
