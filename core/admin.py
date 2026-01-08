from django.contrib import admin
from .models import AuthenticationProfile, MockEndpoint, ResponseHandler


@admin.register(AuthenticationProfile)
class AuthenticationProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'auth_type', 'created_at', 'updated_at')


@admin.register(MockEndpoint)
class MockEndpointAdmin(admin.ModelAdmin):
    list_display = ('path', 'authentication', 'description', 'created_at', 'updated_at', 'creator')


@admin.register(ResponseHandler)
class ResponseHandlerAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'http_method', 'description', 'created_at', 'updated_at')