import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.tenants.models import TenantMembership, UserAccount
from offline_service.knowledge_entry_ingestion import (
    clear_knowledge_entry_index,
    run_knowledge_entry_ingestion,
)

from .models import KnowledgeBase, KnowledgeEntry
from .views import _json_body, _kb_for_tenant, _membership, _tenant

_READ_ROLES = {
    TenantMembership.Role.OWNER,
    TenantMembership.Role.ADMIN,
    TenantMembership.Role.MEMBER,
    TenantMembership.Role.VIEWER,
}
_WRITE_ROLES = {TenantMembership.Role.OWNER, TenantMembership.Role.ADMIN}


def _serialize_entry(e):
    return {
        "id": e.id,
        "knowledge_base_id": e.knowledge_base_id,
        "title": e.title,
        "body": e.body,
        "status": e.status,
        "snapshot_id": e.snapshot_id,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }


@require_http_methods(["GET", "POST"])
@csrf_exempt
def entries_collection(request, kb_id):
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
        rows = KnowledgeEntry.objects.filter(knowledge_base=kb).order_by("-id")
        return JsonResponse({"items": [_serialize_entry(e) for e in rows]})
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    if kb.status != KnowledgeBase.Status.ACTIVE:
        return JsonResponse({"error": "knowledge_base_inactive"}, status=403)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    body = (data.get("body") or "").strip()
    if not body:
        return JsonResponse({"error": "missing_body"}, status=400)
    title = data.get("title")
    if title is not None:
        title = str(title).strip() or None
    st = data.get("status") or KnowledgeEntry.Status.DRAFT
    if st not in (
        KnowledgeEntry.Status.DRAFT,
        KnowledgeEntry.Status.PUBLISHED,
        KnowledgeEntry.Status.ARCHIVED,
    ):
        return JsonResponse({"error": "invalid_status"}, status=400)
    now = timezone.now()
    e = KnowledgeEntry.objects.create(
        tenant=tenant,
        knowledge_base=kb,
        title=title,
        body=body,
        status=st,
        snapshot=None,
        created_at=now,
        updated_at=now,
    )
    if e.status == KnowledgeEntry.Status.PUBLISHED:
        run_knowledge_entry_ingestion(e.id)
    return JsonResponse(_serialize_entry(e), status=201)


@require_http_methods(["GET", "PATCH", "DELETE"])
@csrf_exempt
def entry_detail(request, kb_id, entry_id):
    tenant, err = _tenant(request)
    if err:
        return err
    kb = _kb_for_tenant(tenant, kb_id)
    if not kb:
        return JsonResponse({"error": "not_found"}, status=404)
    try:
        e = KnowledgeEntry.objects.get(pk=entry_id, knowledge_base=kb)
    except KnowledgeEntry.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        return JsonResponse(_serialize_entry(e))
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    if request.method == "DELETE":
        if e.status == KnowledgeEntry.Status.PUBLISHED:
            clear_knowledge_entry_index(e.id)
        e.delete()
        return JsonResponse({"ok": True})
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    prev_status = e.status
    now = timezone.now()
    if "title" in data:
        t = data.get("title")
        e.title = None if t is None else str(t).strip() or None
    if "body" in data:
        b = (data.get("body") or "").strip()
        if not b:
            return JsonResponse({"error": "invalid_body"}, status=400)
        e.body = b
    if "status" in data:
        st = data.get("status")
        if st not in (
            KnowledgeEntry.Status.DRAFT,
            KnowledgeEntry.Status.PUBLISHED,
            KnowledgeEntry.Status.ARCHIVED,
        ):
            return JsonResponse({"error": "invalid_status"}, status=400)
        e.status = st
    e.updated_at = now
    e.save()
    if prev_status == KnowledgeEntry.Status.PUBLISHED and e.status != KnowledgeEntry.Status.PUBLISHED:
        clear_knowledge_entry_index(e.id)
    elif e.status == KnowledgeEntry.Status.PUBLISHED:
        run_knowledge_entry_ingestion(e.id)
    return JsonResponse(_serialize_entry(e))
