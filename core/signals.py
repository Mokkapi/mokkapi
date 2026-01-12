"""
Signal handlers for audit logging authentication events.

Connects to Django's built-in auth signals to log login, logout, and
failed authentication attempts.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .audit import create_audit_log
from .models import AuditLog


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login."""
    create_audit_log(
        user=user,
        action=AuditLog.Action.LOGIN,
        endpoint_id=None,
        old_value=None,
        new_value={'username': user.username}
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout."""
    create_audit_log(
        user=user,
        action=AuditLog.Action.LOGOUT,
        endpoint_id=None,
        old_value=None,
        new_value={'username': user.username if user else 'unknown'}
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    Log failed login attempt.

    CRITICAL: Do NOT log the password - only log the username.
    """
    create_audit_log(
        user=None,  # Failed login = no authenticated user
        action=AuditLog.Action.AUTH_FAILURE,
        endpoint_id=None,
        old_value=None,
        new_value={'username': credentials.get('username', 'unknown')}
        # password is intentionally OMITTED
    )
