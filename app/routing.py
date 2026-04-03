from django.urls import path

from app.apps.conversations.consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/v1/chat", ChatConsumer.as_asgi()),
]
