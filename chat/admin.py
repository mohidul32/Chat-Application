from django.contrib import admin
from .models import ChatRoom, RoomMembership, Message, MessageReaction


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'room_type', 'created_by', 'member_count', 'created_at', 'is_active')
    list_filter = ('room_type', 'is_active', 'created_at')
    search_fields = ('name', 'created_by__username')
    readonly_fields = ('id', 'created_at', 'updated_at')

    def member_count(self, obj):
        return obj.member_count

    member_count.short_description = 'Members'


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'role', 'joined_at', 'is_active', 'unread_count')
    list_filter = ('role', 'is_active', 'is_muted', 'joined_at')
    search_fields = ('user__username', 'room__name')

    def unread_count(self, obj):
        return obj.unread_count

    unread_count.short_description = 'Unread'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'message_type', 'content_preview', 'timestamp', 'is_deleted')
    list_filter = ('message_type', 'is_deleted', 'timestamp')
    search_fields = ('sender__username', 'content', 'room__name')
    readonly_fields = ('id', 'timestamp')

    def content_preview(self, obj):
        if obj.message_type == 'text' and obj.content:
            return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        return f"[{obj.get_message_type_display()}]"

    content_preview.short_description = 'Content'


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'reaction', 'created_at')
    list_filter = ('reaction', 'created_at')
    search_fields = ('user__username', 'message__content')