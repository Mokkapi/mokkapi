from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect
from django.urls import path, include

from core.views import serve_mock_response
# --- Prepare Core App Prefix (with validation) ---
core_prefix = getattr(settings, 'CORE_ENDPOINT_PREFIX', None) # Use your setting name

if not core_prefix:
    raise ImproperlyConfigured(
        "CORE_ENDPOINT_PREFIX is not set in settings.py. Please define it (e.g., '_mokkapi_admin/')."
    )
# Ensure it ends with a slash for include()
if not core_prefix.endswith('/'):
    core_prefix += '/'
# Ensure it doesn't start with a slash (optional)
core_prefix = core_prefix.lstrip('/')
# Basic validation
if not core_prefix or core_prefix == '/':
     raise ImproperlyConfigured("CORE_ENDPOINT_PREFIX cannot be empty or root ('/').")
# Optional: Check for conflicts
if core_prefix.lower().startswith('admin/'):
     print(f"Warning: CORE_ENDPOINT_PREFIX ('{core_prefix}') starts with 'admin/', potential conflict with Django admin.")


# --- Prepare Django Admin Prefix ---
django_admin_prefix = getattr(settings, 'DJANGO_ADMIN_PREFIX', 'admin/')
if not django_admin_prefix.endswith('/'):
    django_admin_prefix += '/'
django_admin_prefix = django_admin_prefix.lstrip('/')

urlpatterns = [
    path(django_admin_prefix, admin.site.urls),
    path(core_prefix, include('core.urls')),
    path('', lambda request: redirect(f'{core_prefix}login/?next=/{core_prefix}', permanent=False), name='root_redirect_to_login'),

    path('<path:endpoint_path>', serve_mock_response, name='serve__mock_response'),
]
