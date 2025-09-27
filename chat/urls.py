from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('room/<uuid:room_id>/', views.chat_room_view, name='room'),
    path('start-chat/<int:user_id>/', views.start_private_chat, name='start_private_chat'),
    path('create-group/', views.create_group_view, name='create_group'),
    path('search-users/', views.search_users, name='search_users'),
    path('leave-room/<uuid:room_id>/', views.leave_room, name='leave_room'),
]