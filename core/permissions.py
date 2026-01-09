# permissions.py (in your app or a common permissions module)
from rest_framework import permissions


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
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions (GET, HEAD, OPTIONS) might be allowed more broadly
        # depending on whether users should be able to see non-owned objects by ID.
        # If ONLY owners/admin should see details, apply check always:
        # return obj.owner == request.user or request.user.is_staff

        # More common: Allow safe methods (GET) if user passed has_permission check,
        # but restrict unsafe methods (PUT, PATCH, DELETE) to owner/admin.
        if request.method in permissions.SAFE_METHODS:
             # Can the user even see *other* people's profiles by ID?
             # If get_queryset already filters to only owned items, this check might
             # be redundant for retrieve, but it's safer to keep it explicit.
             # Let's restrict retrieve as well for profiles for better privacy.
            return obj.owner == request.user or request.user.is_staff
        else: # Unsafe methods (PUT, PATCH, DELETE)
            return obj.owner == request.user or request.user.is_staff