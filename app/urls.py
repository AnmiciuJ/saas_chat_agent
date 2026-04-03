from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/tenants/", include("app.apps.tenants.urls")),
    path("api/v1/inference/", include("app.apps.models_registry.urls")),
    path("api/v1/", include("app.apps.knowledge_base.urls")),
    path("api/v1/", include("app.apps.documents.urls")),
    path("api/v1/", include("online_service.urls")),
    path("api/v1/", include("app.apps.usage.urls")),
    path("api/v1/", include("app.apps.conversations.urls")),
]
