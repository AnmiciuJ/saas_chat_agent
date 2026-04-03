import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.knowledge_base.models import KnowledgeBase
from app.apps.tenants.models import TenantMembership, UserAccount

from .retrieve import run_retrieval

_READ_ROLES = {
    TenantMembership.Role.OWNER,
    TenantMembership.Role.ADMIN,
    TenantMembership.Role.MEMBER,
    TenantMembership.Role.VIEWER,
}


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


@csrf_exempt
@require_http_methods(["POST"])
def retrieve(request, kb_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _READ_ROLES)
    if err:
        return err
    try:
        kb = KnowledgeBase.objects.get(pk=kb_id, tenant=tenant)
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if kb.status != KnowledgeBase.Status.ACTIVE:
        return JsonResponse({"error": "knowledge_base_inactive"}, status=403)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    q = data.get("query")
    top_k = data.get("top_k")
    snap = data.get("snapshot_id")
    tk = None
    if top_k is not None:
        try:
            tk = int(top_k)
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_top_k"}, status=400)
    sid = None
    if snap is not None:
        try:
            sid = int(snap)
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_snapshot_id"}, status=400)
    out = run_retrieval(tenant.id, kb.id, q, top_k=tk, snapshot_id=sid)
    return JsonResponse(out)
