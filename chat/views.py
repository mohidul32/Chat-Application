from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import ChatRoom, RoomMembership, Message, get_or_create_private_chat, create_group_chat
from .forms import MessageForm, GroupChatForm

User = get_user_model()


@login_required
def home_view(request):
    """Chat home page - user এর সব chat rooms show করবে"""

    # User এর যোগ দেয়া সব rooms
    user_memberships = RoomMembership.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('room').prefetch_related('room__members__user')

    # Active rooms list
    rooms = []
    for membership in user_memberships:
        room = membership.room
        room.membership = membership  # Add membership info to room
        room.unread_count = membership.unread_count
        rooms.append(room)

    # All users for starting new chat
    all_users = User.objects.exclude(id=request.user.id).filter(is_active=True)

    context = {
        'rooms': rooms,
        'all_users': all_users,
        'user': request.user
    }

    return render(request, 'chat/home.html', context)


@login_required
def chat_room_view(request, room_id):
    """Individual chat room page"""

    room = get_object_or_404(ChatRoom, id=room_id)

    # Check if user is member of this room
    try:
        membership = RoomMembership.objects.get(room=room, user=request.user, is_active=True)
    except RoomMembership.DoesNotExist:
        messages.error(request, "You don't have permission to access this chat room.")
        return redirect('chat:home')

    # Get messages (latest 50 messages, oldest first for display)
    room_messages = Message.objects.filter(
        room=room,
        is_deleted=False
    ).select_related('sender').prefetch_related('reactions')[:50]
    room_messages = list(reversed(room_messages))  # Show oldest first

    # Mark messages as read
    membership.last_read_at = timezone.now()
    membership.save()

    # Get room members
    room_members = RoomMembership.objects.filter(
        room=room,
        is_active=True
    ).select_related('user')

    # Handle message sending
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.room = room
            message.sender = request.user
            message.save()

            # Update room's updated_at timestamp
            room.updated_at = timezone.now()
            room.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # AJAX request - return JSON response
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': str(message.id),
                        'content': message.content,
                        'sender': message.sender.username,
                        'timestamp': message.timestamp.strftime('%H:%M'),
                        'message_type': message.message_type
                    }
                })

            return redirect('chat:room', room_id=room_id)
    else:
        form = MessageForm()

    context = {
        'room': room,
        'messages': room_messages,
        'members': room_members,
        'membership': membership,
        'form': form
    }

    return render(request, 'chat/room.html', context)


@login_required
def start_private_chat(request, user_id):
    """দুইজন user এর মধ্যে private chat start করা"""

    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        messages.error(request, "You can't start a chat with yourself!")
        return redirect('chat:home')

    # Get or create private chat room
    room = get_or_create_private_chat(request.user, other_user)

    return redirect('chat:room', room_id=room.id)


@login_required
def create_group_view(request):
    """Group chat তৈরি করার page"""

    if request.method == 'POST':
        form = GroupChatForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data.get('description')
            members = form.cleaned_data.get('members', [])

            # Create group chat
            room = create_group_chat(
                creator=request.user,
                name=name,
                description=description,
                members=members
            )

            messages.success(request, f'Group "{name}" created successfully!')
            return redirect('chat:room', room_id=room.id)
    else:
        form = GroupChatForm()

    context = {
        'form': form,
        'all_users': User.objects.exclude(id=request.user.id).filter(is_active=True)
    }

    return render(request, 'chat/create_group.html', context)


@login_required
def search_users(request):
    """User search API for starting new chats"""

    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'users': []})

    users = User.objects.filter(
        Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query),
        is_active=True
    ).exclude(id=request.user.id)[:10]

    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'is_online': user.is_online
        })

    return JsonResponse({'users': users_data})


@login_required
def leave_room(request, room_id):
    """Room থেকে বের হওয়া"""

    room = get_object_or_404(ChatRoom, id=room_id)

    try:
        membership = RoomMembership.objects.get(room=room, user=request.user)

        if room.room_type == 'private':
            messages.error(request, "You can't leave a private chat.")
        else:
            membership.is_active = False
            membership.save()

            # System message
            Message.objects.create(
                room=room,
                sender=request.user,
                message_type='system',
                content=f"{request.user.username} left the group"
            )

            messages.success(request, f'You left "{room.name}"')

    except RoomMembership.DoesNotExist:
        messages.error(request, "You are not a member of this room.")

    return redirect('chat:home')