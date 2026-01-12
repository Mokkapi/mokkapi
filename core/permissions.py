# permissions.py (in your app or a common permissions module)
from rest_framework import permissions

from .audit import create_audit_log
from .models import AuditLog


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission that only allows admin/staff users to access.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admin users to access/modify it.
    Assumes the model instance has an 'owner' attribute.
    """

    def has_permission(self, request, view):
        # Allow access if the user is authenticated (base check)
        is_authenticated = request.user and request.user.is_authenticated

        if not is_authenticated:
            # Log unauthenticated access attempt
            create_audit_log(
                user=None,
                action=AuditLog.Action.AUTH_FAILURE,
                endpoint_id=None,
                old_value=None,
                new_value={
                    'attempted_action': request.method,
                    'path': request.path,
                    'reason': 'unauthenticated'
                }
            )

        return is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions (GET, HEAD, OPTIONS) might be allowed more broadly
        # depending on whether users should be able to see non-owned objects by ID.
        # If ONLY owners/admin should see details, apply check always:
        # return obj.owner == request.user or request.user.is_staff

        # More common: Allow safe methods (GET) if user passed has_permission check,
        # but restrict unsafe methods (PUT, PATCH, DELETE) to owner/admin.
        is_allowed = obj.owner == request.user or request.user.is_staff

        if not is_allowed:
            # Log permission denial
            endpoint_id = getattr(obj, 'id', None) if hasattr(obj, 'path') else getattr(obj, 'endpoint_id', None)
            create_audit_log(
                user=request.user,
                action=AuditLog.Action.PERMISSION_DENIED,
                endpoint_id=endpoint_id,
                old_value=None,
                new_value={
                    'attempted_action': request.method,
                    'resource_type': obj.__class__.__name__,
                    'resource_id': obj.id
                }
            )

        return is_allowed