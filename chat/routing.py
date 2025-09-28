# chat/routing.py - Exact এইভাবে হতে হবে
from django.urls import path, re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>[\w-]+)/$', consumers.ChatConsumer.as_asgi()),
    path('ws/chat/<str:room_id>/', consumers.ChatConsumer.as_asgi()),
]