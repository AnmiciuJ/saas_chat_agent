from django.urls import path

from . import views

urlpatterns = [
    path("knowledge-bases/<int:kb_id>/retrieve", views.retrieve),
]
