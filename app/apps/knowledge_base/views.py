import json

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.models_registry.resolver import resolve_active_embedding_model
from app.apps.tenants.models import TenantMembership, UserAccount

from .models import KnowledgeBase, KnowledgeBaseSnapshot

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


def _kb_quota_ok(tenant):
    plan = tenant.plan
    if not plan or plan.max_knowledge_bases < 0:
        return True
    n = KnowledgeBase.objects.filter(tenant=tenant).count()
    return n < plan.max_knowledge_bases


def _serialize_kb(kb):
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "status": kb.status,
        "embedding_model_id": kb.embedding_model_id,
        "embedding_model_key": kb.embedding_model_key,
        "current_snapshot_id": kb.current_snapshot_id,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    }


def _serialize_snapshot(s):
    return {
        "id": s.id,
        "knowledge_base_id": s.knowledge_base_id,
        "version_label": s.version_label,
        "notes": s.notes,
        "created_by_user_id": s.created_by_user_id,
        "created_at": s.created_at.isoformat(),
    }


def _kb_for_tenant(tenant, kb_id):
    try:
        return KnowledgeBase.objects.get(pk=kb_id, tenant=tenant)
    except KnowledgeBase.DoesNotExist:
        return None


@require_http_methods(["GET", "POST"])
@csrf_exempt
def kb_collection(request):
    tenant, err = _tenant(request)
    if err:
        return err
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        rows = KnowledgeBase.objects.filter(tenant=tenant).order_by("-updated_at", "id")
        return JsonResponse({"items": [_serialize_kb(kb) for kb in rows]})
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "missing_name"}, status=400)
    em_id = data.get("embedding_model_id")
    if em_id is None:
        return JsonResponse({"error": "missing_embedding_model_id"}, status=400)
    em = resolve_active_embedding_model(em_id)
    if not em:
        return JsonResponse({"error": "invalid_embedding_model"}, status=400)
    if not _kb_quota_ok(tenant):
        return JsonResponse({"error": "knowledge_base_quota_exceeded"}, status=403)
    desc = data.get("description")
    if desc is not None:
        desc = str(desc).strip() or None
    now = timezone.now()
    key = f"{em.provider}:{em.model_key}"
    kb = KnowledgeBase.objects.create(
        tenant=tenant,
        name=name,
        description=desc,
        status=KnowledgeBase.Status.ACTIVE,
        embedding_model=em,
        embedding_model_key=key,
        current_snapshot=None,
        created_at=now,
        updated_at=now,
    )
    return JsonResponse(_serialize_kb(kb), status=201)


@require_http_methods(["GET", "PATCH"])
@csrf_exempt
def kb_detail(request, kb_id):
    tenant, err = _tenant(request)
    if err:
        return err
    kb = _kb_for_tenant(tenant, kb_id)
    if not kb:
        return JsonResponse({"error": "not_found"}, status=404)
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        out = _serialize_kb(kb)
        snaps = (
            KnowledgeBaseSnapshot.objects.filter(knowledge_base=kb)
            .order_by("-id")[:200]
        )
        out["snapshots"] = [_serialize_snapshot(s) for s in snaps]
        return JsonResponse(out)
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    now = timezone.now()
    if "name" in data:
        n = (data.get("name") or "").strip()
        if not n:
            return JsonResponse({"error": "invalid_name"}, status=400)
        kb.name = n
    if "description" in data:
        d = data.get("description")
        kb.description = None if d is None else str(d).strip() or None
    if "status" in data:
        st = data.get("status")
        if st not in (KnowledgeBase.Status.ACTIVE, KnowledgeBase.Status.INACTIVE):
            return JsonResponse({"error": "invalid_status"}, status=400)
        kb.status = st
    kb.updated_at = now
    kb.save()
    return JsonResponse(_serialize_kb(kb))


@require_http_methods(["GET", "POST"])
@csrf_exempt
def snapshots_collection(request, kb_id):
    tenant, err = _tenant(request)
    if err:
        return err
    kb = _kb_for_tenant(tenant, kb_id)
    if not kb:
        return JsonResponse({"error": "not_found"}, status=404)
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        rows = KnowledgeBaseSnapshot.objects.filter(knowledge_base=kb).order_by("-id")
        return JsonResponse({"items": [_serialize_snapshot(s) for s in rows]})
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    vl = (data.get("version_label") or "").strip()
    if not vl:
        return JsonResponse({"error": "missing_version_label"}, status=400)
    notes = data.get("notes")
    if notes is not None:
        notes = str(notes).strip() or None
    user = _session_user(request)
    now = timezone.now()
    with transaction.atomic():
        s = KnowledgeBaseSnapshot.objects.create(
            knowledge_base=kb,
            version_label=vl,
            notes=notes,
            created_by_user=user,
            created_at=now,
        )
        kb.current_snapshot = s
        kb.updated_at = now
        kb.save(update_fields=["current_snapshot", "updated_at"])
    return JsonResponse(_serialize_snapshot(s), status=201)


@require_http_methods(["PATCH"])
@csrf_exempt
def current_snapshot_update(request, kb_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    kb = _kb_for_tenant(tenant, kb_id)
    if not kb:
        return JsonResponse({"error": "not_found"}, status=404)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    sid = data.get("snapshot_id")
    if sid is None:
        return JsonResponse({"error": "missing_snapshot_id"}, status=400)
    try:
        s = KnowledgeBaseSnapshot.objects.get(pk=int(sid), knowledge_base=kb)
    except (ValueError, KnowledgeBaseSnapshot.DoesNotExist):
        return JsonResponse({"error": "invalid_snapshot"}, status=400)
    now = timezone.now()
    kb.current_snapshot = s
    kb.updated_at = now
    kb.save(update_fields=["current_snapshot", "updated_at"])
    return JsonResponse(_serialize_kb(kb))
