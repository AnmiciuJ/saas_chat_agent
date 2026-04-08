"""
用量计量服务。

提供用量事件记录与按日汇总能力，供对话链路和异步任务调用。
"""

import logging
from datetime import datetime, timezone, date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SyncSessionLocal
from app.models.usage import UsageEvent, UsageDailyAggregate

logger = logging.getLogger(__name__)


def record_chat_usage(
    tenant_id: int,
    conversation_id: int,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """记录一轮对话产生的用量事件（轮次 + Token）。"""
    now = datetime.now(timezone.utc)
    with SyncSessionLocal() as session:
        session.add(UsageEvent(
            tenant_id=tenant_id,
            event_type="chat_turn",
            quantity=1,
            unit="turns",
            conversation_id=conversation_id,
            occurred_at=now,
        ))
        if prompt_tokens > 0:
            session.add(UsageEvent(
                tenant_id=tenant_id,
                event_type="prompt_tokens",
                quantity=prompt_tokens,
                unit="tokens",
                conversation_id=conversation_id,
                occurred_at=now,
            ))
        if completion_tokens > 0:
            session.add(UsageEvent(
                tenant_id=tenant_id,
                event_type="completion_tokens",
                quantity=completion_tokens,
                unit="tokens",
                conversation_id=conversation_id,
                occurred_at=now,
            ))
        session.commit()


def record_storage_usage(
    tenant_id: int,
    document_id: int,
    size_bytes: int,
) -> None:
    """记录文档存储用量。"""
    with SyncSessionLocal() as session:
        session.add(UsageEvent(
            tenant_id=tenant_id,
            event_type="storage_bytes",
            quantity=size_bytes,
            unit="bytes",
            document_id=document_id,
            occurred_at=datetime.now(timezone.utc),
        ))
        session.commit()


def refresh_daily_aggregate(tenant_id: int, target_date: date | None = None) -> None:
    """
    汇总指定日期的用量事件并写入/更新日汇总表。

    默认汇总当天数据。
    """
    bucket = target_date or date.today()
    day_start = datetime(bucket.year, bucket.month, bucket.day, tzinfo=timezone.utc)
    day_end = datetime(bucket.year, bucket.month, bucket.day, 23, 59, 59, tzinfo=timezone.utc)

    with SyncSessionLocal() as session:
        events = session.execute(
            select(UsageEvent).where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.occurred_at >= day_start,
                UsageEvent.occurred_at <= day_end,
            )
        ).scalars().all()

        totals = {
            "chat_turns": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "storage_bytes": 0,
        }
        for e in events:
            if e.event_type == "chat_turn":
                totals["chat_turns"] += int(e.quantity)
            elif e.event_type == "prompt_tokens":
                totals["prompt_tokens"] += int(e.quantity)
            elif e.event_type == "completion_tokens":
                totals["completion_tokens"] += int(e.quantity)
            elif e.event_type == "storage_bytes":
                totals["storage_bytes"] += int(e.quantity)

        existing = session.execute(
            select(UsageDailyAggregate).where(
                UsageDailyAggregate.tenant_id == tenant_id,
                UsageDailyAggregate.bucket_date == bucket,
            )
        ).scalar_one_or_none()

        if existing:
            existing.chat_turns = totals["chat_turns"]
            existing.prompt_tokens = totals["prompt_tokens"]
            existing.completion_tokens = totals["completion_tokens"]
            existing.storage_bytes = totals["storage_bytes"]
        else:
            session.add(UsageDailyAggregate(
                tenant_id=tenant_id,
                bucket_date=bucket,
                **totals,
            ))
        session.commit()
    logger.info("日汇总已更新: tenant_id=%s, date=%s", tenant_id, bucket)
