from django.db.models import F
from django.utils import timezone

from .models import UsageDailyAggregate, UsageEvent


def record_chat_usage(tenant_id, conversation_id, prompt_tokens, completion_tokens, occurred_at=None):
    oc = occurred_at or timezone.now()
    UsageEvent.objects.create(
        tenant_id=tenant_id,
        event_type=UsageEvent.EventType.CHAT_TURN,
        quantity=1,
        unit="turns",
        conversation_id=conversation_id,
        document_id=None,
        reference_id=None,
        occurred_at=oc,
        extra=None,
    )
    pt = int(prompt_tokens or 0)
    ct = int(completion_tokens or 0)
    if pt > 0:
        UsageEvent.objects.create(
            tenant_id=tenant_id,
            event_type=UsageEvent.EventType.PROMPT_TOKENS,
            quantity=pt,
            unit="tokens",
            conversation_id=conversation_id,
            document_id=None,
            reference_id=None,
            occurred_at=oc,
            extra=None,
        )
    if ct > 0:
        UsageEvent.objects.create(
            tenant_id=tenant_id,
            event_type=UsageEvent.EventType.COMPLETION_TOKENS,
            quantity=ct,
            unit="tokens",
            conversation_id=conversation_id,
            document_id=None,
            reference_id=None,
            occurred_at=oc,
            extra=None,
        )
    bucket = oc.date()
    agg, _ = UsageDailyAggregate.objects.get_or_create(
        tenant_id=tenant_id,
        bucket_date=bucket,
        defaults={
            "chat_turns": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "storage_bytes": 0,
            "updated_at": oc,
        },
    )
    UsageDailyAggregate.objects.filter(pk=agg.pk).update(
        chat_turns=F("chat_turns") + 1,
        prompt_tokens=F("prompt_tokens") + pt,
        completion_tokens=F("completion_tokens") + ct,
        updated_at=oc,
    )
