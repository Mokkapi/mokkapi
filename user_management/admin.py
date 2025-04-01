# user_management/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ExtendedGroup, GroupObjectPermission, ChangeLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_ldap_user')
    # Customize further as needed

@admin.register(ExtendedGroup)
class ExtendedGroupAdmin(admin.ModelAdmin):
    list_display = ('group', 'description')

@admin.register(GroupObjectPermission)
class GroupObjectPermissionAdmin(admin.ModelAdmin):
    list_display = ('group', 'permission_type', 'content_type', 'object_id')
    list_filter = ('group', 'permission_type', 'content_type')

@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'action', 'timestamp')
    list_filter = ('user', 'content_type', 'action')
    readonly_fields = ('user', 'content_type', 'object_id', 'action', 'timestamp', 'changes')