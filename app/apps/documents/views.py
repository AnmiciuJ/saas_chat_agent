import hashlib
import json

import config
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.knowledge_base.models import KnowledgeBase, KnowledgeBaseSnapshot
from app.apps.tenants.models import TenantMembership, UserAccount

from offline_service.ingestion import run_ingestion_job

from .models import Document, IngestionJob
from .storage import write_object

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


def _kb_for_tenant(tenant, kb_id):
    try:
        return KnowledgeBase.objects.get(pk=kb_id, tenant=tenant)
    except KnowledgeBase.DoesNotExist:
        return None


def _doc_quota_ok(tenant):
    plan = tenant.plan
    if not plan or plan.max_documents_total < 0:
        return True
    n = Document.objects.filter(tenant=tenant).count()
    return n < plan.max_documents_total


def _storage_key(tenant_id, document_id):
    return f"tenants/{tenant_id}/documents/{document_id}/original"


def _serialize_doc(d):
    return {
        "id": d.id,
        "tenant_id": d.tenant_id,
        "knowledge_base_id": d.knowledge_base_id,
        "snapshot_id": d.snapshot_id,
        "source_type": d.source_type,
        "source_url": d.source_url,
        "original_filename": d.original_filename,
        "storage_bucket": d.storage_bucket,
        "storage_key": d.storage_key,
        "mime_type": d.mime_type,
        "size_bytes": d.size_bytes,
        "content_sha256": d.content_sha256,
        "parse_status": d.parse_status,
        "index_status": d.index_status,
        "last_error": d.last_error,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


def _serialize_job(j):
    return {
        "id": j.id,
        "tenant_id": j.tenant_id,
        "document_id": j.document_id,
        "job_type": j.job_type,
        "status": j.status,
        "progress_percent": j.progress_percent,
        "worker_task_id": j.worker_task_id,
        "attempt_count": j.attempt_count,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        "error_detail": j.error_detail,
        "created_at": j.created_at.isoformat(),
        "updated_at": j.updated_at.isoformat(),
    }


def _resolve_snapshot_id(kb, raw):
    if raw is None:
        return None, None
    try:
        s = KnowledgeBaseSnapshot.objects.get(pk=int(raw), knowledge_base=kb)
    except (ValueError, KnowledgeBaseSnapshot.DoesNotExist):
        return None, JsonResponse({"error": "invalid_snapshot"}, status=400)
    return s.id, None


@require_http_methods(["GET", "POST"])
@csrf_exempt
def documents_collection(request, kb_id):
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
        rows = Document.objects.filter(knowledge_base=kb).order_by("-id")
        return JsonResponse({"items": [_serialize_doc(d) for d in rows]})
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    if not _doc_quota_ok(tenant):
        return JsonResponse({"error": "document_quota_exceeded"}, status=403)
    if kb.status != KnowledgeBase.Status.ACTIVE:
        return JsonResponse({"error": "knowledge_base_inactive"}, status=403)
    ct = (request.content_type or "").split(";")[0].strip().lower()
    now = timezone.now()
    bucket = (config.OBJECT_STORAGE_BUCKET or "").strip() or "local"
    if request.FILES.get("file"):
        f = request.FILES.get("file")
        if not f:
            return JsonResponse({"error": "missing_file"}, status=400)
        data = f.read()
        size = len(data)
        mime = f.content_type or "application/octet-stream"
        orig = f.name or "upload"
        sid, err = _resolve_snapshot_id(kb, request.POST.get("snapshot_id"))
        if err:
            return err
        profile = {"ingest_target_snapshot_id": sid} if sid is not None else None
        doc = Document.objects.create(
            tenant=tenant,
            knowledge_base=kb,
            snapshot=None,
            source_type=Document.SourceType.FILE_UPLOAD,
            source_url=None,
            original_filename=orig[:512],
            storage_bucket=bucket,
            storage_key="pending",
            mime_type=mime[:128] if mime else None,
            size_bytes=size,
            content_sha256=hashlib.sha256(data).hexdigest(),
            parse_status=Document.ParseStatus.PENDING,
            index_status=Document.IndexStatus.PENDING,
            chunk_profile_json=profile,
            created_at=now,
            updated_at=now,
        )
        key = _storage_key(tenant.id, doc.id)
        Document.objects.filter(pk=doc.pk).update(storage_key=key)
        write_object(key, data)
    elif ct == "application/json":
        try:
            body = _json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)
        st = body.get("source_type")
        if st != Document.SourceType.URL_IMPORT:
            return JsonResponse({"error": "unsupported_source_type"}, status=400)
        url = (body.get("source_url") or "").strip()
        if not url:
            return JsonResponse({"error": "missing_source_url"}, status=400)
        orig = (body.get("original_filename") or "").strip() or "url"
        sid, err = _resolve_snapshot_id(kb, body.get("snapshot_id"))
        if err:
            return err
        profile = {"ingest_target_snapshot_id": sid} if sid is not None else None
        payload = url.encode("utf-8")
        size = len(payload)
        doc = Document.objects.create(
            tenant=tenant,
            knowledge_base=kb,
            snapshot=None,
            source_type=Document.SourceType.URL_IMPORT,
            source_url=url[:2048],
            original_filename=orig[:512],
            storage_bucket=bucket,
            storage_key="pending",
            mime_type="text/plain",
            size_bytes=size,
            content_sha256=hashlib.sha256(payload).hexdigest(),
            parse_status=Document.ParseStatus.PENDING,
            index_status=Document.IndexStatus.PENDING,
            chunk_profile_json=profile,
            created_at=now,
            updated_at=now,
        )
        key = _storage_key(tenant.id, doc.id)
        Document.objects.filter(pk=doc.pk).update(storage_key=key)
        write_object(key, payload)
    else:
        return JsonResponse({"error": "expected_multipart_or_json"}, status=400)
    job = IngestionJob.objects.create(
        tenant=tenant,
        document=doc,
        job_type=IngestionJob.JobType.FULL_PIPELINE,
        status=IngestionJob.Status.QUEUED,
        progress_percent=None,
        worker_task_id=None,
        attempt_count=0,
        created_at=now,
        updated_at=now,
    )
    run_ingestion_job(job.id)
    doc.refresh_from_db()
    return JsonResponse(_serialize_doc(doc), status=201)


@require_http_methods(["GET"])
def document_detail(request, doc_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _READ_ROLES)
    if err:
        return err
    try:
        doc = Document.objects.get(pk=doc_id, tenant=tenant)
    except Document.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    return JsonResponse(_serialize_doc(doc))


@require_http_methods(["GET"])
def ingestion_jobs_list(request, doc_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _READ_ROLES)
    if err:
        return err
    try:
        doc = Document.objects.get(pk=doc_id, tenant=tenant)
    except Document.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    rows = IngestionJob.objects.filter(document=doc).order_by("-id")
    return JsonResponse({"items": [_serialize_job(j) for j in rows]})


@require_http_methods(["GET"])
def ingestion_job_detail(request, job_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _READ_ROLES)
    if err:
        return err
    try:
        job = IngestionJob.objects.get(pk=job_id, tenant=tenant)
    except IngestionJob.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    return JsonResponse(_serialize_job(job))
