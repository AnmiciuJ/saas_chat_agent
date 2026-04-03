from django.urls import path

from . import views

urlpatterns = [
    path("end-user-profiles", views.end_user_profiles_collection),
    path("end-user-profiles/<int:profile_id>", views.end_user_profile_detail),
    path("conversations/<int:conv_id>/profile", views.conversation_profile_bind),
]
