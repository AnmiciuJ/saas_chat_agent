from django.db import models


class EmbeddingModel(models.Model):
    provider = models.CharField(max_length=64)
    model_key = models.CharField(max_length=128)
    display_name = models.CharField(max_length=256)
    vector_dimension = models.IntegerField()
    is_active = models.BooleanField()
    extra_config = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "embedding_model"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "model_key"],
                name="uniq_embedding_model_provider_key",
            ),
        ]


class InferenceBaseModel(models.Model):
    provider = models.CharField(max_length=64)
    model_key = models.CharField(max_length=128)
    display_name = models.CharField(max_length=256)
    modality = models.CharField(max_length=32)
    max_context_tokens = models.IntegerField(null=True, blank=True)
    supports_streaming = models.BooleanField()
    is_active = models.BooleanField()
    extra_config = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "base_model"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "model_key"],
                name="uniq_base_model_provider_key",
            ),
        ]


class TenantModelBinding(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="model_bindings",
    )
    base_model = models.ForeignKey(
        InferenceBaseModel,
        on_delete=models.CASCADE,
        related_name="tenant_bindings",
    )
    is_default = models.BooleanField()
    priority = models.IntegerField()
    enabled = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "tenant_model_binding"


class FineTuneJob(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "draft"
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"
        CANCELLED = "cancelled", "cancelled"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="fine_tune_jobs",
    )
    base_model = models.ForeignKey(
        InferenceBaseModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fine_tune_jobs",
    )
    parent_fine_tune_job = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_jobs",
    )
    version_label = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    dataset_storage_key = models.CharField(max_length=1024, null=True, blank=True)
    log_storage_key = models.CharField(max_length=1024, null=True, blank=True)
    output_model_ref = models.CharField(max_length=512, null=True, blank=True)
    metrics = models.JSONField(null=True, blank=True)
    evaluation_summary = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "fine_tune_job"
