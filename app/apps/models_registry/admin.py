from django.contrib import admin

from .models import EmbeddingModel, FineTuneJob, InferenceBaseModel, TenantModelBinding


@admin.register(EmbeddingModel)
class EmbeddingModelAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "model_key", "display_name", "vector_dimension", "is_active")
    search_fields = ("provider", "model_key", "display_name")


@admin.register(InferenceBaseModel)
class InferenceBaseModelAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "model_key", "display_name", "modality", "is_active")
    list_filter = ("is_active", "provider")
    search_fields = ("provider", "model_key", "display_name")


@admin.register(TenantModelBinding)
class TenantModelBindingAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "base_model", "is_default", "priority", "enabled")
    list_filter = ("enabled", "is_default")


@admin.register(FineTuneJob)
class FineTuneJobAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "status", "version_label", "created_at")
    list_filter = ("status",)
