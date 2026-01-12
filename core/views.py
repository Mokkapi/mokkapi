from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from rest_framework import generics, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

import base64
import json
import logging
import secrets

from .models import AuthenticationProfile, MockEndpoint, ResponseHandler, AuditLog
from .permissions import IsOwnerOrAdmin, IsAdminUser
from .serializers import AuthenticationProfileSerializer, MockEndpointCreateSerializer, MockEndpointSerializer, ResponseHandlerSerializer, AuditLogSerializer
from .utils import build_tree_data_structure, check_authentication
from .audit import create_audit_log, serialize_model_state


logger = logging.getLogger(__name__)

class AuthenticationProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to view and manage their Authentication Profiles.
    """
    serializer_class = AuthenticationProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff: # Admins can see all profiles
             return AuthenticationProfile.objects.all().order_by('owner__username', 'name')
        # Regular users only see their own
        return AuthenticationProfile.objects.filter(owner=user).order_by('name')


    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.CREATE,
            endpoint_id=None,
            old_value=None,
            new_value=serialize_model_state(instance)
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        old_value = serialize_model_state(instance)
        instance = serializer.save()
        new_value = serialize_model_state(instance)
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.UPDATE,
            endpoint_id=None,
            old_value=old_value,
            new_value=new_value
        )

    def perform_destroy(self, instance):
        old_value = serialize_model_state(instance)
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.DELETE,
            endpoint_id=None,
            old_value=old_value,
            new_value=None
        )

class MockEndpointViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Mock Endpoints and their Handlers.
    """
    queryset = MockEndpoint.objects.prefetch_related('handlers').order_by('path')
    permission_classes = [IsOwnerOrAdmin]  # IsOwnerOrAdmin includes auth check with logging

    lookup_field = 'id'

    def get_queryset(self):
        """Filter endpoints by owner for list views, allow all for detail views (permission check happens there)."""
        user = self.request.user
        if not user.is_authenticated:
            return MockEndpoint.objects.none()
        # For list action, filter by owner (unless admin)
        if self.action == 'list':
            if user.is_staff:
                return MockEndpoint.objects.prefetch_related('handlers').order_by('path')
            return MockEndpoint.objects.filter(owner=user).prefetch_related('handlers').order_by('path')
        # For detail views (retrieve, update, destroy), return all - permission check will happen
        return MockEndpoint.objects.prefetch_related('handlers').order_by('path')

    def get_serializer_class(self):
        """Use specific serializer for 'create' action."""
        if self.action == 'create':
            return MockEndpointCreateSerializer
        return MockEndpointSerializer # Default for other actions

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def list(self, request, *args, **kwargs):
        """List endpoints with audit logging."""
        response = super().list(request, *args, **kwargs)
        create_audit_log(
            user=request.user,
            action=AuditLog.Action.READ,
            endpoint_id=None,
            old_value=None,
            new_value=None
        )
        return response

    def retrieve(self, request, *args, **kwargs):
        """Retrieve endpoint with audit logging."""
        response = super().retrieve(request, *args, **kwargs)
        instance = self.get_object()
        create_audit_log(
            user=request.user,
            action=AuditLog.Action.READ,
            endpoint_id=instance.id,
            old_value=None,
            new_value=serialize_model_state(instance)
        )
        return response

    def perform_create(self, serializer):
        """Set creator/owner and log CREATE."""
        instance = serializer.save(creator=self.request.user, owner=self.request.user)
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.CREATE,
            endpoint_id=instance.id,
            old_value=None,
            new_value=serialize_model_state(instance)
        )

    def perform_update(self, serializer):
        """Set updated_by and log UPDATE."""
        instance = self.get_object()
        old_value = serialize_model_state(instance)
        instance = serializer.save(updated_by=self.request.user)
        new_value = serialize_model_state(instance)
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.UPDATE,
            endpoint_id=instance.id,
            old_value=old_value,
            new_value=new_value
        )

    def perform_destroy(self, instance):
        """Log DELETE before deletion."""
        old_value = serialize_model_state(instance)
        endpoint_id = instance.id
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.DELETE,
            endpoint_id=endpoint_id,
            old_value=old_value,
            new_value=None
        )

    @action(detail=True, methods=['post'], url_path='handlers', serializer_class=ResponseHandlerSerializer)
    def create_handler(self, request, path=None):
        """
        Add a new Response Handler to this specific Mock Endpoint.
        POST /api/endpoints/{path}/handlers/
        """
        endpoint = self.get_object() # Gets the MockEndpoint instance based on path
        serializer = self.get_serializer(data=request.data) # Use ResponseHandlerSerializer
        serializer.is_valid(raise_exception=True)

        # Check for duplicate method manually before saving
        http_method = serializer.validated_data.get('http_method', '').upper()
        if endpoint.handlers.filter(http_method=http_method).exists():
             return Response(
                 {'error': f"A handler for method '{http_method}' already exists for this endpoint."},
                 status=status.HTTP_400_BAD_REQUEST
             )

        # Link handler to the endpoint and save
        handler = serializer.save(endpoint=endpoint)
        create_audit_log(
            user=request.user,
            action=AuditLog.Action.CREATE,
            endpoint_id=endpoint.id,
            old_value=None,
            new_value=serialize_model_state(handler)
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'], url_path='handlers/(?P<handler_pk>[^/.]+)', serializer_class=ResponseHandlerSerializer)
    def retrieve_handler(self, request, path=None, handler_pk=None):
        """
        Retrieve a specific Response Handler by its PK, nested under an endpoint.
        GET /api/endpoints/{path}/handlers/{handler_pk}/
        """
        endpoint = self.get_object() # Ensure endpoint exists and user has permission
        handler = get_object_or_404(ResponseHandler, pk=handler_pk, endpoint=endpoint)
        serializer = self.get_serializer(handler)
        return Response(serializer.data)

    @action(detail=True, methods=['put', 'patch'], url_path='handlers/(?P<handler_pk>[^/.]+)', serializer_class=ResponseHandlerSerializer)
    def update_handler(self, request, path=None, handler_pk=None):
        """
        Update a specific Response Handler by its PK.
        PUT/PATCH /api/endpoints/{path}/handlers/{handler_pk}/
        """
        endpoint = self.get_object() # Ensure endpoint exists
        handler = get_object_or_404(ResponseHandler, pk=handler_pk, endpoint=endpoint)
        serializer = self.get_serializer(handler, data=request.data, partial=request.method == 'PATCH')
        serializer.is_valid(raise_exception=True)

        # Prevent changing http_method via this action? Optional.
        # if 'http_method' in serializer.validated_data and serializer.validated_data['http_method'].upper() != handler.http_method:
        #     return Response({'error': 'Cannot change HTTP method via update.'}, status=status.HTTP_400_BAD_REQUEST)

        old_value = serialize_model_state(handler)
        serializer.save()
        new_value = serialize_model_state(handler)
        create_audit_log(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            endpoint_id=endpoint.id,
            old_value=old_value,
            new_value=new_value
        )
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='handlers/(?P<handler_pk>[^/.]+)')
    def destroy_handler(self, request, path=None, handler_pk=None):
        """
        Delete a specific Response Handler by its PK.
        DELETE /api/endpoints/{path}/handlers/{handler_pk}/
        """
        endpoint = self.get_object() # Ensure endpoint exists
        handler = get_object_or_404(ResponseHandler, pk=handler_pk, endpoint=endpoint)
        old_value = serialize_model_state(handler)
        handler.delete()
        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            endpoint_id=endpoint.id,
            old_value=old_value,
            new_value=None
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

def react_app(request):
    if not request.user.is_authenticated:
        return redirect('mokkapi/login')
    return render(request, 'mokkapi/react_app.html', {
        "app_config": {
            "apiPrefix": settings.CORE_ENDPOINT_PREFIX,
            }
        })

def whoami(request):
    return JsonResponse({
        "is_authenticated": request.user.is_authenticated,
        "is_staff":        request.user.is_staff,
        "username":        request.user.username,
    })

@login_required
def admin_view(request):
    return render(request, 'mokkapi/admin.html')

@login_required # Protect the management UI home page
def home_view(request):
    if request.method != 'GET':
        # Should not happen if routing is correct, but good safeguard
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET'])

    try:
        endpoints_with_handlers = MockEndpoint.objects.prefetch_related('handlers').filter().order_by('path')
        auth_profiles = AuthenticationProfile.objects.filter(owner=request.user).order_by('name')
        # Prepare data for the template
        structured_data = build_tree_data_structure(list(endpoints_with_handlers))
        auth_profiles_list = [{'id': p.id, 'name': p.name} for p in auth_profiles]
        context = {
            'structured_endpoints_json': json.dumps(structured_data),
            'auth_profiles_json': json.dumps(auth_profiles_list),
        }
        return render(request, 'mokkapi/home.html', context)

    except Exception as e:
         logger.error(f"Error processing GET request for home_view: {e}", exc_info=True)
         context = {'error_message': 'Failed to load page data.'}
         return render(request, 'mokkapi/home.html', context)

def serve_mock_response(request, endpoint_path):
    """
    Finds the MockEndpoint by path, performs authentication, finds the
    appropriate ResponseHandler by method, and returns the mocked response.
    """
    normalized_path = '/'.join(filter(None, endpoint_path.strip().split('/')))

    try:
         mock_endpoint = get_object_or_404(MockEndpoint.objects.select_related('authentication'), path=normalized_path)
    except Http404:
         raise  # Let Django handle 404
    except Exception as e:
         # TODO log this error
         return JsonResponse({'error': 'Internal Server Error during endpoint lookup.'}, status=500)

    is_authenticated, auth_response = check_authentication(request, mock_endpoint.authentication)
    if not is_authenticated:
        # Log authentication failure
        create_audit_log(
            user=None,
            action=AuditLog.Action.AUTH_FAILURE,
            endpoint_id=mock_endpoint.id,
            old_value=None,
            new_value={
                'http_method': request.method,
                'path': normalized_path,
                'auth_type': mock_endpoint.authentication.auth_type if mock_endpoint.authentication else None
            }
        )
        return auth_response

    try:
        handler = mock_endpoint.handlers.filter(http_method=request.method.upper()).first()
    except Exception as e:
        # TODO log this error
        return JsonResponse({'error': 'Internal Server Error during handler lookup.'}, status=500)

    if handler is None:
        # Find allowed methods for the Allow header
        allowed_methods = list(mock_endpoint.handlers.values_list('http_method', flat=True).distinct())
        allow_header = ", ".join(sorted(allowed_methods)) # Format nicely
        response = JsonResponse({'error': f'Method {request.method} not allowed.'}, status=405)
        response['Allow'] = allow_header
        return response

    try:
        response_headers = handler.response_headers or {} # must be a dict
        content_type = response_headers.get('Content-Type', 'text/plain') # Default fallback

        response = HttpResponse(
            content=handler.response_body,
            status=handler.response_status_code,
            content_type=content_type
        )

        # Add other headers from the handler's JSON field
        for key, value in response_headers.items():
            if key.lower() != 'content-type':
                 response[key] = value

        # Log successful mock endpoint access
        create_audit_log(
            user=None,
            action=AuditLog.Action.READ,
            endpoint_id=mock_endpoint.id,
            old_value=None,
            new_value={
                'http_method': request.method,
                'path': normalized_path,
                'status_code': handler.response_status_code
            }
        )
        return response

    except Exception as e:
        # TODO log this error
        return JsonResponse({'error': 'Internal Server Error building response.'}, status=500)

class ResponseHandlerViewSet(viewsets.ModelViewSet):
    queryset = ResponseHandler.objects.select_related('endpoint')
    serializer_class = ResponseHandlerSerializer
    permission_classes = [permissions.IsAuthenticated]

    # TODO figure out why the delete option successfully deletes the handler, but still runs into a "does not exist" error.

    def perform_create(self, serializer):
        # you could optionally verify that request.data['endpoint']
        # really belongs to this user's endpoints, etc.
        handler = serializer.save()  # full_clean is called here by default
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.CREATE,
            endpoint_id=handler.endpoint_id,
            old_value=None,
            new_value=serialize_model_state(handler)
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        old_value = serialize_model_state(instance)
        handler = serializer.save()
        new_value = serialize_model_state(handler)
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.UPDATE,
            endpoint_id=handler.endpoint_id,
            old_value=old_value,
            new_value=new_value
        )

    def perform_destroy(self, instance):
        old_value = serialize_model_state(instance)
        endpoint_id = instance.endpoint_id
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.DELETE,
            endpoint_id=endpoint_id,
            old_value=old_value,
            new_value=None
        )

    def get_queryset(self):
        qs = super().get_queryset()
        endpoint = self.request.query_params.get('endpoint')
        if endpoint:
            qs = qs.filter(endpoint__path=endpoint)  # or endpoint__id=endpoint
        return qs


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing audit logs (admin only).
    Read-only - audit logs cannot be created, updated, or deleted via API.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """
        Only admin users can view audit logs.
        Supports filtering by user, action, and endpoint_id.
        """
        if not self.request.user.is_staff:
            return AuditLog.objects.none()

        queryset = AuditLog.objects.select_related('user').order_by('-timestamp')

        # Optional filters
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action.upper())

        endpoint_id = self.request.query_params.get('endpoint_id')
        if endpoint_id:
            queryset = queryset.filter(endpoint_id=endpoint_id)

        return queryset


@login_required
def audit_logs_view(request):
    """
    Web view for displaying audit logs (admin only).
    """
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You do not have permission to view audit logs.")

    # Get filter parameters
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')

    # Get audit logs with optional filters
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')

    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)

    # Limit to last 100 entries for performance
    logs = logs[:100]

    # Get action choices for filter dropdown
    action_choices = AuditLog.Action.choices

    context = {
        'logs': logs,
        'action_choices': action_choices,
        'current_action_filter': action_filter,
        'current_user_filter': user_filter,
    }
    return render(request, 'mokkapi/audit_logs.html', context)