from django.db import models


class TenantApiCredential(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        REVOKED = "revoked", "revoked"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="api_credentials",
    )
    name = models.CharField(max_length=128)
    key_id = models.CharField(max_length=64, unique=True)
    secret_hash = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=Status.choices)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "tenant_api_credential"
        indexes = [
            models.Index(fields=["tenant_id"]),
        ]
