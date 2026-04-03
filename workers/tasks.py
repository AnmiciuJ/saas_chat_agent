def run_ingestion_job_task(job_id):
    from offline_service.ingestion import run_ingestion_job

    run_ingestion_job(job_id)
