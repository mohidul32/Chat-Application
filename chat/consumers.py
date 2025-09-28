# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatRoom, Message, RoomMembership

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        print(f"[WebSocket] Connection attempt by {self.user} to room {self.room_id}")

        if not self.user.is_authenticated:
            print("[WebSocket] User not authenticated")
            await self.close()
            return

        # Check room permission
        has_permission = await self.check_room_permission()
        if not has_permission:
            print("[WebSocket] User has no permission for this room")
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print(f"[WebSocket] Added {self.user} to group {self.room_group_name}")

        await self.accept()

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': f'{self.user.username} connected to chat room!'
        }))

    async def disconnect(self, close_code):
        print(f"[WebSocket] {self.user} disconnected from {self.room_group_name}")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print(f"[WebSocket] Received from {self.user}: {text_data}")
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                message_content = data.get('message', '').strip()
                if message_content:
                    print(f"[WebSocket] Processing message: {message_content}")

                    # Save to database
                    message = await self.save_message(message_content)

                    if message:
                        print(f"[WebSocket] Message saved, broadcasting to group {self.room_group_name}")

                        # Send to group
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'chat_message',
                                'message': {
                                    'id': str(message.id),
                                    'content': message.content,
                                    'sender': message.sender.username,
                                    'timestamp': message.timestamp.strftime('%H:%M'),
                                }
                            }
                        )
                    else:
                        print("[WebSocket] Failed to save message")

        except json.JSONDecodeError as e:
            print(f"[WebSocket] JSON decode error: {e}")
        except Exception as e:
            print(f"[WebSocket] Error in receive: {e}")

    # Handle message from room group
    async def chat_message(self, event):
        message = event['message']
        print(f"[WebSocket] Broadcasting message to {self.user}: {message}")

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    @database_sync_to_async
    def check_room_permission(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            membership = RoomMembership.objects.get(
                room=room,
                user=self.user,
                is_active=True
            )
            print(f"[WebSocket] Room permission OK for {self.user}")
            return True
        except (ChatRoom.DoesNotExist, RoomMembership.DoesNotExist) as e:
            print(f"[WebSocket] Room permission failed: {e}")
            return False

    @database_sync_to_async
    def save_message(self, content):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                message_type='text'
            )

            # Update room timestamp
            room.updated_at = timezone.now()
            room.save()

            print(f"[WebSocket] Message saved to DB: {message.id}")
            return message
        except Exception as e:
            print(f"[WebSocket] Error saving message: {e}")
            return None