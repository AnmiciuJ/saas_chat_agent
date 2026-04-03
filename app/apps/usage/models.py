from django.db import models


class UsageEvent(models.Model):
    class EventType(models.TextChoices):
        CHAT_TURN = "chat_turn", "chat_turn"
        PROMPT_TOKENS = "prompt_tokens", "prompt_tokens"
        COMPLETION_TOKENS = "completion_tokens", "completion_tokens"
        STORAGE_BYTES = "storage_bytes", "storage_bytes"
        API_CALL = "api_call", "api_call"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="usage_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    unit = models.CharField(max_length=32)
    conversation = models.ForeignKey(
        "conversations.Conversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="usage_events",
    )
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="usage_events",
    )
    reference_id = models.CharField(max_length=128, null=True, blank=True)
    occurred_at = models.DateTimeField()
    extra = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "usage_event"
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["occurred_at"]),
        ]


class UsageDailyAggregate(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="usage_daily_aggregates",
    )
    bucket_date = models.DateField()
    chat_turns = models.BigIntegerField()
    prompt_tokens = models.BigIntegerField()
    completion_tokens = models.BigIntegerField()
    storage_bytes = models.BigIntegerField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "usage_daily_aggregate"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "bucket_date"],
                name="uniq_usage_daily_tenant_date",
            ),
        ]
