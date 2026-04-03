from django.urls import path

from . import entry_views, views

urlpatterns = [
    path("knowledge-bases", views.kb_collection),
    path("knowledge-bases/<int:kb_id>", views.kb_detail),
    path("knowledge-bases/<int:kb_id>/snapshots", views.snapshots_collection),
    path("knowledge-bases/<int:kb_id>/current-snapshot", views.current_snapshot_update),
    path(
        "knowledge-bases/<int:kb_id>/entries",
        entry_views.entries_collection,
    ),
    path(
        "knowledge-bases/<int:kb_id>/entries/<int:entry_id>",
        entry_views.entry_detail,
    ),
]
