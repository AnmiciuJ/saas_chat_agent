from django.db import models


class EndUserProfile(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="end_user_profiles",
    )
    external_user_key = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256, null=True, blank=True)
    preference_json = models.JSONField(null=True, blank=True)
    tag_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "end_user_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_user_key"],
                name="uniq_end_user_profile_tenant_external_key",
            ),
        ]


class Conversation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "open"
        CLOSED = "closed", "closed"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    knowledge_base = models.ForeignKey(
        "knowledge_base.KnowledgeBase",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    user_account = models.ForeignKey(
        "tenants.UserAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    end_user_profile = models.ForeignKey(
        EndUserProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    title = models.CharField(max_length=512, null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "conversation"
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["user_account_id"]),
            models.Index(fields=["last_message_at"]),
        ]


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "user"
        ASSISTANT = "assistant", "assistant"
        SYSTEM = "system", "system"
        TOOL = "tool", "tool"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sequence = models.IntegerField()
    role = models.CharField(max_length=32, choices=Role.choices)
    content = models.TextField()
    used_base_model = models.ForeignKey(
        "models_registry.InferenceBaseModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_messages",
    )
    rewritten_query = models.TextField(null=True, blank=True)
    pipeline_trace = models.JSONField(null=True, blank=True)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    retrieval_refs = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "chat_message"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence"],
                name="uniq_chat_message_conversation_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["conversation_id"]),
        ]


class ConversationMemoryChunk(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="conversation_memory_chunks",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memory_chunks",
    )
    source_message = models.ForeignKey(
        ChatMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memory_chunks",
    )
    chunk_index = models.IntegerField()
    text_content = models.TextField()
    vector_point_id = models.CharField(max_length=128, null=True, blank=True)
    embedding_model_key = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "conversation_memory_chunk"
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["conversation_id"]),
        ]
