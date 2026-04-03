import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.apps.tenants.models import TenantMembership
from offline_service.finetune.placeholder import run_finetune_placeholder

from .models import FineTuneJob, InferenceBaseModel
from .views import _json_body, _membership, _tenant

_READ_ROLES = {
    TenantMembership.Role.OWNER,
    TenantMembership.Role.ADMIN,
    TenantMembership.Role.MEMBER,
    TenantMembership.Role.VIEWER,
}
_WRITE_ROLES = {TenantMembership.Role.OWNER, TenantMembership.Role.ADMIN}


def _serialize_job(j):
    return {
        "id": j.id,
        "base_model_id": j.base_model_id,
        "parent_fine_tune_job_id": j.parent_fine_tune_job_id,
        "version_label": j.version_label,
        "status": j.status,
        "dataset_storage_key": j.dataset_storage_key,
        "log_storage_key": j.log_storage_key,
        "output_model_ref": j.output_model_ref,
        "metrics": j.metrics,
        "evaluation_summary": j.evaluation_summary,
        "error_message": j.error_message,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        "created_at": j.created_at.isoformat(),
        "updated_at": j.updated_at.isoformat(),
    }


@require_http_methods(["GET", "POST"])
@csrf_exempt
def fine_tune_jobs_collection(request):
    tenant, err = _tenant(request)
    if err:
        return err
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        rows = FineTuneJob.objects.filter(tenant=tenant).order_by("-id")
        return JsonResponse({"items": [_serialize_job(j) for j in rows]})
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    ds = (data.get("dataset_storage_key") or "").strip()
    if not ds:
        return JsonResponse({"error": "missing_dataset_storage_key"}, status=400)
    bm = None
    if data.get("base_model_id") is not None:
        try:
            bm = InferenceBaseModel.objects.get(pk=int(data["base_model_id"]), is_active=True)
        except (ValueError, InferenceBaseModel.DoesNotExist):
            return JsonResponse({"error": "invalid_base_model"}, status=400)
    parent = None
    if data.get("parent_fine_tune_job_id") is not None:
        try:
            parent = FineTuneJob.objects.get(
                pk=int(data["parent_fine_tune_job_id"]),
                tenant=tenant,
            )
        except (ValueError, FineTuneJob.DoesNotExist):
            return JsonResponse({"error": "invalid_parent_job"}, status=400)
    vl = data.get("version_label")
    if vl is not None:
        vl = str(vl).strip() or None
    now = timezone.now()
    j = FineTuneJob.objects.create(
        tenant=tenant,
        base_model=bm,
        parent_fine_tune_job=parent,
        version_label=vl,
        status=FineTuneJob.Status.DRAFT,
        dataset_storage_key=ds[:1024],
        log_storage_key=None,
        output_model_ref=None,
        metrics=None,
        evaluation_summary=None,
        error_message=None,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    return JsonResponse(_serialize_job(j), status=201)


@require_http_methods(["GET", "PATCH"])
@csrf_exempt
def fine_tune_job_detail(request, job_id):
    tenant, err = _tenant(request)
    if err:
        return err
    try:
        j = FineTuneJob.objects.get(pk=job_id, tenant=tenant)
    except FineTuneJob.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if request.method == "GET":
        _, err = _membership(request, tenant, _READ_ROLES)
        if err:
            return err
        return JsonResponse(_serialize_job(j))
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    if data.get("status") == FineTuneJob.Status.CANCELLED:
        if j.status not in (
            FineTuneJob.Status.DRAFT,
            FineTuneJob.Status.QUEUED,
            FineTuneJob.Status.RUNNING,
        ):
            return JsonResponse({"error": "invalid_status"}, status=400)
        now = timezone.now()
        FineTuneJob.objects.filter(pk=j.pk).update(
            status=FineTuneJob.Status.CANCELLED,
            finished_at=now,
            updated_at=now,
        )
        j.refresh_from_db()
        return JsonResponse(_serialize_job(j))
    return JsonResponse({"error": "unsupported_patch"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def fine_tune_job_run(request, job_id):
    tenant, err = _tenant(request)
    if err:
        return err
    _, err = _membership(request, tenant, _WRITE_ROLES)
    if err:
        return err
    try:
        j = FineTuneJob.objects.get(pk=job_id, tenant=tenant)
    except FineTuneJob.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if j.status != FineTuneJob.Status.DRAFT:
        return JsonResponse({"error": "invalid_status"}, status=400)
    if not (j.dataset_storage_key or "").strip():
        return JsonResponse({"error": "missing_dataset_storage_key"}, status=400)
    now = timezone.now()
    FineTuneJob.objects.filter(pk=j.pk).update(
        status=FineTuneJob.Status.QUEUED,
        updated_at=now,
    )
    run_finetune_placeholder(j.id)
    j.refresh_from_db()
    return JsonResponse(_serialize_job(j))

