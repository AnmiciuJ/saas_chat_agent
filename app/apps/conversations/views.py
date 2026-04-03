import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.tenants.models import TenantMembership, UserAccount

from .models import Conversation, EndUserProfile

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


def _serialize_profile(p):
    return {
        "id": p.id,
        "external_user_key": p.external_user_key,
        "display_name": p.display_name,
        "preference_json": p.preference_json,
        "tag_json": p.tag_json,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


@require_http_methods(["GET", "POST"])
@csrf_exempt
def end_user_profiles_collection(request):
    tenant, err = _tenant(request)
    if err:
        return err
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        rows = EndUserProfile.objects.filter(tenant=tenant).order_by("-id")
        return JsonResponse({"items": [_serialize_profile(p) for p in rows]})
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    ext = (data.get("external_user_key") or "").strip()
    if not ext:
        return JsonResponse({"error": "missing_external_user_key"}, status=400)
    if EndUserProfile.objects.filter(tenant=tenant, external_user_key=ext).exists():
        return JsonResponse({"error": "external_key_taken"}, status=409)
    now = timezone.now()
    dn = data.get("display_name")
    if dn is not None:
        dn = str(dn).strip() or None
    p = EndUserProfile.objects.create(
        tenant=tenant,
        external_user_key=ext[:256],
        display_name=dn,
        preference_json=data.get("preference_json"),
        tag_json=data.get("tag_json"),
        created_at=now,
        updated_at=now,
    )
    return JsonResponse(_serialize_profile(p), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
@csrf_exempt
def end_user_profile_detail(request, profile_id):
    tenant, err = _tenant(request)
    if err:
        return err
    try:
        p = EndUserProfile.objects.get(pk=profile_id, tenant=tenant)
    except EndUserProfile.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        return JsonResponse(_serialize_profile(p))
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    if request.method == "DELETE":
        p.delete()
        return JsonResponse({"ok": True})
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    now = timezone.now()
    if "display_name" in data:
        d = data.get("display_name")
        p.display_name = None if d is None else str(d).strip() or None
    if "preference_json" in data:
        p.preference_json = data.get("preference_json")
    if "tag_json" in data:
        p.tag_json = data.get("tag_json")
    p.updated_at = now
    p.save()
    return JsonResponse(_serialize_profile(p))


@csrf_exempt
@require_http_methods(["PATCH"])
def conversation_profile_bind(request, conv_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        conv = Conversation.objects.get(pk=conv_id, tenant=tenant)
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    pid = data.get("end_user_profile_id")
    if pid is None:
        conv.end_user_profile = None
    else:
        try:
            prof = EndUserProfile.objects.get(pk=int(pid), tenant=tenant)
        except (ValueError, EndUserProfile.DoesNotExist):
            return JsonResponse({"error": "invalid_profile"}, status=400)
        conv.end_user_profile = prof
    conv.updated_at = timezone.now()
    conv.save(update_fields=["end_user_profile", "updated_at"])
    return JsonResponse(
        {
            "id": conv.id,
            "end_user_profile_id": conv.end_user_profile_id,
        }
    )
