from django.contrib.auth.hashers import check_password
from django.utils import timezone

from app.apps.api.models import TenantApiCredential


def parse_sk_token(token):
    if not token or not token.startswith("sk_"):
        return None, None
    body = token[3:]
    if len(body) < 34:
        return None, None
    key_id = body[:32]
    if body[32] != "_":
        return None, None
    secret = body[33:]
    if not secret:
        return None, None
    return key_id, secret


def resolve_api_key(token):
    key_id, secret = parse_sk_token((token or "").strip())
    if not key_id:
        return None
    try:
        cred = TenantApiCredential.objects.select_related("tenant").get(
            key_id=key_id,
            status=TenantApiCredential.Status.ACTIVE,
        )
    except TenantApiCredential.DoesNotExist:
        return None
    now = timezone.now()
    if cred.expires_at and cred.expires_at < now:
        return None
    if not check_password(secret, cred.secret_hash):
        return None
    TenantApiCredential.objects.filter(pk=cred.pk).update(last_used_at=now)
    return cred
