from django.urls import path

from . import views

urlpatterns = [
    path("knowledge-bases/<int:kb_id>/documents", views.documents_collection),
    path("documents/<int:doc_id>/ingestion-jobs", views.ingestion_jobs_list),
    path("documents/<int:doc_id>", views.document_detail),
    path("ingestion-jobs/<int:job_id>", views.ingestion_job_detail),
]
