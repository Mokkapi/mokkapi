from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

core_prefix = getattr(settings, 'CORE_ENDPOINT_PREFIX', None) 
if not core_prefix:
    raise ImproperlyConfigured(
        "CORE_ENDPOINT_PREFIX is not set in settings.py. Please define it (e.g., '_mokkapi_admin/')."
    )

class SetContextMiddleware:

    def process_template_response(self, request, response):
        response.context_data['mokkapi_core_prefix'] = core_prefix
        return response