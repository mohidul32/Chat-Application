from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class ChatRoom(models.Model):
    """Chat Room Model - Individual বা Group chat এর জন্য"""

    ROOM_TYPES = [
        ('private', 'Private Chat'),
        ('group', 'Group Chat'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)  # Group চ্যাটের জন্য
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='private')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # Group chat এর জন্য additional fields
    description = models.TextField(blank=True, null=True)
    max_members = models.IntegerField(default=100)  # Group size limit

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.room_type == 'group':
            return self.name or f"Group Chat {self.id}"
        else:
            # Private chat এর জন্য participants দের নাম show করবে
            members = self.members.all()[:2]
            if len(members) >= 2:
                return f"{members[0].user.username} & {members[1].user.username}"
            return f"Private Chat {self.id}"

    @property
    def member_count(self):
        return self.members.count()

    @property
    def last_message(self):
        return self.messages.first()  # ordering এর কারণে first = latest


class RoomMembership(models.Model):
    """Room এ কে কে member আছে"""

    MEMBER_ROLES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    role = models.CharField(max_length=10, choices=MEMBER_ROLES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Message notifications
    is_muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['room', 'user']  # Same user can't join same room twice
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.room}"

    @property
    def unread_count(self):
        """Unread messages count"""
        return self.room.messages.filter(
            timestamp__gt=self.last_read_at
        ).exclude(sender=self.user).count()


class Message(models.Model):
    """Individual Messages"""

    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System Message'),  # যেমন "User joined", "User left" etc
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')

    # Message content
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True, null=True)  # Text content

    # File uploads
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)

    # Message metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    # Reply functionality
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='replies')

    class Meta:
        ordering = ['-timestamp']  # Latest first

    def __str__(self):
        if self.message_type == 'text':
            preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
            return f"{self.sender.username}: {preview}"
        else:
            return f"{self.sender.username}: {self.get_message_type_display()}"

    @property
    def is_edited(self):
        return self.edited_at is not None

    def soft_delete(self):
        """Message delete করার পরিবর্তে hide করবে"""
        self.is_deleted = True
        self.content = "This message was deleted"
        self.save()


class MessageReaction(models.Model):
    """Message reactions (like, love, laugh etc)"""

    REACTION_TYPES = [
        ('👍', 'Like'),
        ('❤️', 'Love'),
        ('😂', 'Laugh'),
        ('😮', 'Wow'),
        ('😢', 'Sad'),
        ('😠', 'Angry'),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    reaction = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'reaction']  # Same user can't give same reaction twice

    def __str__(self):
        return f"{self.user.username} {self.reaction} on {self.message.id}"


# Helper functions for chat operations
def get_or_create_private_chat(user1, user2):
    """দুইজন user এর মধ্যে private chat room তৈরি করে বা existing টা return করে"""

    # Check if private chat already exists between these users
    existing_rooms = ChatRoom.objects.filter(
        room_type='private',
        members__user=user1
    ).filter(
        members__user=user2
    ).distinct()

    if existing_rooms.exists():
        return existing_rooms.first()

    # Create new private chat room
    room = ChatRoom.objects.create(
        room_type='private',
        created_by=user1
    )

    # Add both users as members
    RoomMembership.objects.create(room=room, user=user1, role='admin')
    RoomMembership.objects.create(room=room, user=user2, role='member')

    return room


def create_group_chat(creator, name, description=None, members=None):
    """Group chat তৈরি করে"""

    room = ChatRoom.objects.create(
        name=name,
        room_type='group',
        description=description,
        created_by=creator
    )

    # Add creator as admin
    RoomMembership.objects.create(room=room, user=creator, role='admin')

    # Add other members
    if members:
        for user in members:
            if user != creator:  # Don't add creator twice
                RoomMembership.objects.create(room=room, user=user, role='member')

    # System message for room creation
    Message.objects.create(
        room=room,
        sender=creator,
        message_type='system',
        content=f"{creator.username} created the group '{name}'"
    )

    return room