from django.db import models


class Plan(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    max_knowledge_bases = models.IntegerField()
    max_documents_total = models.IntegerField()
    max_storage_bytes = models.BigIntegerField()
    max_monthly_chat_turns = models.IntegerField()
    max_monthly_tokens = models.BigIntegerField()
    features = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "plan"


class Tenant(models.Model):
    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "pending_review"
        ACTIVE = "active", "active"
        SUSPENDED = "suspended", "suspended"
        ARCHIVED = "archived", "archived"

    name = models.CharField(max_length=256)
    slug = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    contact_email = models.CharField(max_length=255)
    plan = models.ForeignKey(
        Plan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tenants",
    )
    review_note = models.TextField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "tenant"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["plan_id"]),
        ]


class UserAccount(models.Model):
    email = models.CharField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    display_name = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField()
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "user_account"


class TenantMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "owner"
        ADMIN = "admin", "admin"
        MEMBER = "member", "member"
        VIEWER = "viewer", "viewer"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user_account = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="tenant_memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "tenant_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user_account"],
                name="uniq_tenant_membership_tenant_user",
            ),
        ]
