import json
import secrets
import uuid

from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.api.models import TenantApiCredential
from app.apps.tenants.models import TenantMembership, UserAccount

_WRITE_ROLES = {TenantMembership.Role.OWNER, TenantMembership.Role.ADMIN}


def _json_body(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _session_user(request):
    uid = request.session.get("user_account_id")
    if not uid:
        return None
    return UserAccount.objects.filter(pk=uid, is_active=True).first()


def _tenant(request):
    if not request.tenant:
        return None, JsonResponse({"error": "tenant_required"}, status=400)
    return request.tenant, None


def _membership(request, tenant, roles):
    user = _session_user(request)
    if not user:
        return None, JsonResponse({"error": "unauthorized"}, status=401)
    m = TenantMembership.objects.filter(tenant=tenant, user_account=user).first()
    if not m or m.role not in roles:
        return None, JsonResponse({"error": "forbidden"}, status=403)
    return m, None


def _serialize_cred(c):
    out = {
        "id": c.id,
        "name": c.name,
        "key_id": c.key_id,
        "status": c.status,
        "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "created_at": c.created_at.isoformat(),
    }
    return out


@require_http_methods(["GET", "POST"])
@csrf_exempt
def api_credentials_collection(request):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    if request.method == "GET":
        rows = TenantApiCredential.objects.filter(tenant=tenant).order_by("-id")
        return JsonResponse({"items": [_serialize_cred(c) for c in rows]})
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "missing_name"}, status=400)
    key_id = uuid.uuid4().hex
    secret = secrets.token_hex(24)
    full = f"sk_{key_id}_{secret}"
    now = timezone.now()
    c = TenantApiCredential.objects.create(
        tenant=tenant,
        name=name[:128],
        key_id=key_id,
        secret_hash=make_password(secret),
        status=TenantApiCredential.Status.ACTIVE,
        last_used_at=None,
        expires_at=None,
        created_at=now,
        updated_at=now,
    )
    out = _serialize_cred(c)
    out["secret_once"] = full
    return JsonResponse(out, status=201)


@csrf_exempt
@require_http_methods(["PATCH"])
def api_credentials_detail(request, cred_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        c = TenantApiCredential.objects.get(pk=cred_id, tenant=tenant)
    except TenantApiCredential.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    if data.get("status") == TenantApiCredential.Status.REVOKED:
        now = timezone.now()
        c.status = TenantApiCredential.Status.REVOKED
        c.updated_at = now
        c.save(update_fields=["status", "updated_at"])
        return JsonResponse(_serialize_cred(c))
    return JsonResponse({"error": "unsupported_patch"}, status=400)
