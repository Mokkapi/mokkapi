# user_management/middleware.py
from threading import local

_thread_locals = local()

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        response = self.get_response(request)
        return response

# Utility function to get current user
def get_current_user():
    return getattr(_thread_locals, 'user', None)