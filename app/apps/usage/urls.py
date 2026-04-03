from django.urls import path

from . import views

urlpatterns = [
    path("api-credentials", views.api_credentials_collection),
    path("api-credentials/<int:cred_id>", views.api_credentials_detail),
]
