"""
Admin configuration for the accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for the LMS User model.
    Adds the 'role' and 'phone' fields to the standard Django user admin.
    """
    model = User

    # List display columns
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

    # Add role and phone to the fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('LMS Role & Profile', {
            'fields': ('role', 'assigned_department', 'phone', 'profile_picture'),
        }),
    )

    # Include role in the add user form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('LMS Role & Profile', {
            'fields': ('role', 'assigned_department', 'email', 'first_name', 'last_name', 'phone'),
        }),
    )
