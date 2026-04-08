"""
Celery 应用实例。

所有异步任务通过此实例注册与调度。
启动命令：celery -A workers.celery_app worker --loglevel=info
"""

from celery import Celery

import config

celery = Celery(
    "saas_chat_agent",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.autodiscover_tasks(["workers.tasks"])
