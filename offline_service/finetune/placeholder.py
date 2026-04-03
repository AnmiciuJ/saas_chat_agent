from django.utils import timezone

from app.apps.models_registry.models import FineTuneJob


def run_finetune_placeholder(job_id):
    job = FineTuneJob.objects.get(pk=job_id)
    if job.status in (
        FineTuneJob.Status.SUCCEEDED,
        FineTuneJob.Status.FAILED,
        FineTuneJob.Status.CANCELLED,
    ):
        return
    now = timezone.now()
    FineTuneJob.objects.filter(pk=job.pk).update(
        status=FineTuneJob.Status.RUNNING,
        started_at=now,
        updated_at=now,
    )
    log_key = job.log_storage_key or (
        f"tenants/{job.tenant_id}/fine_tune/{job.id}/logs/placeholder.log"
    )
    now2 = timezone.now()
    FineTuneJob.objects.filter(pk=job.pk).update(
        status=FineTuneJob.Status.SUCCEEDED,
        finished_at=now2,
        updated_at=now2,
        log_storage_key=log_key,
        output_model_ref=f"placeholder:ft:{job.id}",
        metrics={"loss": 0.01, "placeholder": True},
        evaluation_summary="placeholder",
    )
