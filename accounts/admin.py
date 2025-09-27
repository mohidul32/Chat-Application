# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Display fields in admin list
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_online', 'last_seen', 'is_staff', 'date_joined')

    # Filter options
    list_filter = ('is_online', 'is_staff', 'is_active', 'date_joined', 'last_seen')

    # Search fields
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # Fields to show when editing user
    fieldsets = UserAdmin.fieldsets + (
        ('Chat Info', {'fields': ('is_online', 'last_seen')}),
    )

    # Read-only fields
    readonly_fields = ('last_seen', 'date_joined')

    # Ordering
    ordering = ('-date_joined',)