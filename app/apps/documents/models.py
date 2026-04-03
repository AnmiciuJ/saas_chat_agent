from django.db import models


class Document(models.Model):
    class SourceType(models.TextChoices):
        FILE_UPLOAD = "file_upload", "file_upload"
        URL_IMPORT = "url_import", "url_import"
        API_PUSH = "api_push", "api_push"

    class ParseStatus(models.TextChoices):
        PENDING = "pending", "pending"
        PROCESSING = "processing", "processing"
        READY = "ready", "ready"
        FAILED = "failed", "failed"

    class IndexStatus(models.TextChoices):
        PENDING = "pending", "pending"
        PROCESSING = "processing", "processing"
        READY = "ready", "ready"
        FAILED = "failed", "failed"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    knowledge_base = models.ForeignKey(
        "knowledge_base.KnowledgeBase",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    snapshot = models.ForeignKey(
        "knowledge_base.KnowledgeBaseSnapshot",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    source_url = models.CharField(max_length=2048, null=True, blank=True)
    original_filename = models.CharField(max_length=512)
    storage_bucket = models.CharField(max_length=128, null=True, blank=True)
    storage_key = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=128, null=True, blank=True)
    size_bytes = models.BigIntegerField()
    content_sha256 = models.CharField(max_length=64, null=True, blank=True)
    parse_status = models.CharField(max_length=32, choices=ParseStatus.choices)
    index_status = models.CharField(max_length=32, choices=IndexStatus.choices)
    last_error = models.TextField(null=True, blank=True)
    chunk_profile_json = models.JSONField(null=True, blank=True)
    extracted_aux_storage_key = models.CharField(max_length=1024, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "document"
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["knowledge_base_id"]),
            models.Index(fields=["parse_status"]),
        ]


class IngestionJob(models.Model):
    class JobType(models.TextChoices):
        PARSE = "parse", "parse"
        CHUNK = "chunk", "chunk"
        EMBED = "embed", "embed"
        INDEX = "index", "index"
        FULL_PIPELINE = "full_pipeline", "full_pipeline"

    class Status(models.TextChoices):
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"
        CANCELLED = "cancelled", "cancelled"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="ingestion_jobs",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="ingestion_jobs",
    )
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    status = models.CharField(max_length=32, choices=Status.choices)
    progress_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    worker_task_id = models.CharField(max_length=128, null=True, blank=True)
    attempt_count = models.IntegerField()
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_detail = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "ingestion_job"


class DocumentChunk(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="document_chunks",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.IntegerField()
    text_content = models.TextField()
    char_count = models.IntegerField()
    vector_point_id = models.CharField(max_length=128, null=True, blank=True)
    embedding_model_key = models.CharField(max_length=128, null=True, blank=True)
    snapshot = models.ForeignKey(
        "knowledge_base.KnowledgeBaseSnapshot",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="document_chunks",
    )
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "document_chunk"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="uniq_document_chunk_document_index",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["vector_point_id"]),
        ]
