import json

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.tenants.models import TenantMembership, UserAccount

from .models import EmbeddingModel, InferenceBaseModel, TenantModelBinding

_READ_ROLES = {
    TenantMembership.Role.OWNER,
    TenantMembership.Role.ADMIN,
    TenantMembership.Role.MEMBER,
    TenantMembership.Role.VIEWER,
}
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


def _serialize_base(m):
    return {
        "id": m.id,
        "provider": m.provider,
        "model_key": m.model_key,
        "display_name": m.display_name,
        "modality": m.modality,
        "max_context_tokens": m.max_context_tokens,
        "supports_streaming": m.supports_streaming,
    }


def _serialize_embedding(m):
    return {
        "id": m.id,
        "provider": m.provider,
        "model_key": m.model_key,
        "display_name": m.display_name,
        "vector_dimension": m.vector_dimension,
    }


def _serialize_binding(b):
    return {
        "id": b.id,
        "base_model_id": b.base_model_id,
        "provider": b.base_model.provider,
        "model_key": b.base_model.model_key,
        "display_name": b.base_model.display_name,
        "is_default": b.is_default,
        "priority": b.priority,
        "enabled": b.enabled,
    }


@require_http_methods(["GET"])
def base_models_catalog(request):
    rows = InferenceBaseModel.objects.filter(is_active=True).order_by("provider", "model_key")
    return JsonResponse({"items": [_serialize_base(m) for m in rows]})


@require_http_methods(["GET"])
def embedding_models_catalog(request):
    rows = EmbeddingModel.objects.filter(is_active=True).order_by("provider", "model_key")
    return JsonResponse({"items": [_serialize_embedding(m) for m in rows]})


@require_http_methods(["GET", "POST"])
@csrf_exempt
def bindings_collection(request):
    if request.method == "GET":
        tenant, err = _tenant(request)
        if err:
            return err
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        rows = TenantModelBinding.objects.filter(tenant=tenant).select_related("base_model").order_by(
            "priority", "id"
        )
        return JsonResponse({"items": [_serialize_binding(b) for b in rows]})
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    bid = data.get("base_model_id")
    if bid is None:
        return JsonResponse({"error": "missing_base_model_id"}, status=400)
    try:
        bm = InferenceBaseModel.objects.get(pk=int(bid), is_active=True)
    except (ValueError, InferenceBaseModel.DoesNotExist):
        return JsonResponse({"error": "invalid_base_model"}, status=400)
    if TenantModelBinding.objects.filter(tenant=tenant, base_model=bm).exists():
        return JsonResponse({"error": "already_bound"}, status=409)
    is_default = bool(data.get("is_default", False))
    priority = int(data.get("priority", 0))
    enabled = bool(data.get("enabled", True))
    now = timezone.now()
    with transaction.atomic():
        if is_default:
            TenantModelBinding.objects.filter(tenant=tenant).update(is_default=False)
        b = TenantModelBinding.objects.create(
            tenant=tenant,
            base_model=bm,
            is_default=is_default,
            priority=priority,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )
    return JsonResponse(_serialize_binding(b), status=201)


@require_http_methods(["PATCH", "DELETE"])
@csrf_exempt
def binding_detail(request, binding_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    if request.method == "DELETE":
        n, _ = TenantModelBinding.objects.filter(pk=binding_id, tenant=tenant).delete()
        if not n:
            return JsonResponse({"error": "not_found"}, status=404)
        return JsonResponse({"ok": True})
    try:
        b = TenantModelBinding.objects.select_related("base_model").get(
            pk=binding_id, tenant=tenant
        )
    except TenantModelBinding.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    now = timezone.now()
    with transaction.atomic():
        if "is_default" in data and bool(data["is_default"]):
            TenantModelBinding.objects.filter(tenant=tenant).exclude(pk=b.pk).update(
                is_default=False
            )
            b.is_default = True
        elif "is_default" in data:
            b.is_default = bool(data["is_default"])
        if "priority" in data:
            b.priority = int(data["priority"])
        if "enabled" in data:
            b.enabled = bool(data["enabled"])
        b.updated_at = now
        b.save()
    b.refresh_from_db()
    return JsonResponse(_serialize_binding(b))
