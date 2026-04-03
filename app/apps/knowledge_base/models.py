from django.db import models


class KnowledgeBase(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        INACTIVE = "inactive", "inactive"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="knowledge_bases",
    )
    name = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    embedding_model = models.ForeignKey(
        "models_registry.EmbeddingModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_bases",
    )
    embedding_model_key = models.CharField(max_length=128, null=True, blank=True)
    current_snapshot = models.ForeignKey(
        "KnowledgeBaseSnapshot",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="current_for_bases",
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "knowledge_base"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="uniq_knowledge_base_tenant_name",
            ),
        ]


class KnowledgeBaseSnapshot(models.Model):
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    version_label = models.CharField(max_length=64)
    notes = models.TextField(null=True, blank=True)
    created_by_user = models.ForeignKey(
        "tenants.UserAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_kb_snapshots",
    )
    created_at = models.DateTimeField()

    class Meta:
        db_table = "knowledge_base_snapshot"


class KnowledgeEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "draft"
        PUBLISHED = "published", "published"
        ARCHIVED = "archived", "archived"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="knowledge_entries",
    )
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    title = models.CharField(max_length=512, null=True, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices)
    snapshot = models.ForeignKey(
        KnowledgeBaseSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_entries",
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "knowledge_entry"


class KnowledgeEntryChunk(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="knowledge_entry_chunks",
    )
    knowledge_entry = models.ForeignKey(
        KnowledgeEntry,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.IntegerField()
    text_content = models.TextField()
    char_count = models.IntegerField()
    vector_point_id = models.CharField(max_length=128, null=True, blank=True)
    embedding_model_key = models.CharField(max_length=128, null=True, blank=True)
    snapshot = models.ForeignKey(
        KnowledgeBaseSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_entry_chunks",
    )
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "knowledge_entry_chunk"
        constraints = [
            models.UniqueConstraint(
                fields=["knowledge_entry", "chunk_index"],
                name="uniq_knowledge_entry_chunk_entry_index",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["vector_point_id"]),
        ]
