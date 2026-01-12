"""
Audit logging helper functions for the core app.

Provides utilities for serializing model state and creating audit log entries.
"""
from datetime import datetime, date
from decimal import Decimal
from django.db.models import Model
from django.db.models.fields.files import FieldFile


# Fields to EXCLUDE from audit logs per model (sensitive data)
SENSITIVE_FIELDS = {
    'AuthenticationProfile': [
        'api_key',
        'basic_auth_password_hash',
        'password',
    ],
}

# Fields to always exclude
ALWAYS_EXCLUDE = ['_state', '_original_state']


def serialize_model_state(instance, exclude_fields=None):
    """
    Serialize a model instance to a JSON-compatible dictionary.
    Excludes sensitive fields and handles related objects.

    Args:
        instance: Django model instance
        exclude_fields: Additional fields to exclude

    Returns:
        dict: JSON-serializable representation of the model state
    """
    if instance is None:
        return None

    exclude_fields = set(exclude_fields or [])

    # Get model-specific sensitive fields
    model_name = instance.__class__.__name__
    sensitive = set(SENSITIVE_FIELDS.get(model_name, []))
    exclude_fields.update(sensitive)
    exclude_fields.update(ALWAYS_EXCLUDE)

    result = {}

    for field in instance._meta.get_fields():
        # Skip reverse relations and many-to-many
        if field.one_to_many or field.many_to_many:
            continue

        field_name = field.name

        # Skip excluded fields
        if field_name in exclude_fields:
            continue

        # Skip any field containing sensitive keywords
        if any(keyword in field_name.lower() for keyword in ['password', 'secret', 'token', 'credential']):
            if field_name not in ['basic_auth_username']:  # Allow username
                continue

        try:
            value = getattr(instance, field_name, None)

            # Handle ForeignKey - store the ID
            if field.is_relation and field.many_to_one:
                fk_id = getattr(instance, f'{field_name}_id', None)
                result[field_name] = fk_id
            # Handle datetime
            elif isinstance(value, datetime):
                result[field_name] = value.isoformat()
            # Handle date
            elif isinstance(value, date):
                result[field_name] = value.isoformat()
            # Handle Decimal
            elif isinstance(value, Decimal):
                result[field_name] = float(value)
            # Handle file fields
            elif isinstance(value, FieldFile):
                result[field_name] = value.name if value else None
            # Handle model instances (shouldn't happen often due to FK handling above)
            elif isinstance(value, Model):
                result[field_name] = value.pk
            # Handle other JSON-serializable values
            else:
                result[field_name] = value

        except Exception:
            # Skip fields that can't be serialized
            continue

    return result


def create_audit_log(user, action, endpoint_id=None, old_value=None, new_value=None):
    """
    Create an AuditLog entry.

    Args:
        user: User instance or None for anonymous/unauthenticated
        action: AuditLog.Action choice (string like 'CREATE', 'READ', etc.)
        endpoint_id: Integer ID of related endpoint (for endpoint/handler actions)
        old_value: dict of previous state (None for CREATE)
        new_value: dict of new state (None for DELETE)

    Returns:
        AuditLog: The created audit log entry
    """
    from .models import AuditLog

    # Handle anonymous/unauthenticated users
    if user and hasattr(user, 'is_authenticated') and not user.is_authenticated:
        user = None

    return AuditLog.objects.create(
        user=user,
        action=action,
        endpoint_id=endpoint_id,
        old_value=old_value,
        new_value=new_value
    )
