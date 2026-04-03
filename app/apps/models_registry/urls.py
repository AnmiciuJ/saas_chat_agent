from django.urls import path

from . import finetune_views, views

urlpatterns = [
    path("base-models", views.base_models_catalog),
    path("embedding-models", views.embedding_models_catalog),
    path("bindings", views.bindings_collection),
    path("bindings/<int:binding_id>", views.binding_detail),
    path("fine-tune-jobs", finetune_views.fine_tune_jobs_collection),
    path("fine-tune-jobs/<int:job_id>", finetune_views.fine_tune_job_detail),
    path("fine-tune-jobs/<int:job_id>/run", finetune_views.fine_tune_job_run),
]
