from django.contrib import admin
from .models import AuthenticationProfile, MockEndpoint, ResponseHandler, AuditLog


@admin.register(AuthenticationProfile)
class AuthenticationProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'auth_type', 'created_at', 'updated_at')


@admin.register(MockEndpoint)
class MockEndpointAdmin(admin.ModelAdmin):
    list_display = ('path', 'authentication', 'description', 'created_at', 'updated_at', 'creator')


@admin.register(ResponseHandler)
class ResponseHandlerAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'http_method', 'description', 'created_at', 'updated_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'endpoint_id')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action')
    readonly_fields = ('user', 'action', 'endpoint_id', 'timestamp', 'old_value', 'new_value')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False  # Audit logs cannot be created via admin

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs cannot be modified

    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs cannot be deleted