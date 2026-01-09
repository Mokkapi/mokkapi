from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.db import models
from user_management.models import UserTrackedModel

import json
import secrets
import uuid

class AuthenticationProfile(models.Model):
    """
    Stores credentials for different authentication methods that can be applied to endpoints.
    """
    class AuthType(models.TextChoices):
        API_KEY = 'API_KEY', 'API Key'
        BASIC = 'BASIC', 'HTTP Basic Auth'
        # Add more types here later, e.g., BEARER = 'BEARER', 'Bearer Token'

    name = models.CharField(
        max_length=100,
        unique=True, # Ensure names are unique for easier selection
        help_text="A unique, user-friendly name for this authentication profile (e.g., 'Admin Key', 'Partner Basic Auth')."
    )
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        help_text="The type of authentication this profile uses."
    )

    # --- API Key Fields ---
    api_key = models.CharField(
        max_length=128, # Store the key itself
        unique=True,
        blank=True, # Can be blank if type is not API_KEY
        null=True,  # Allow NULL in DB
        db_index=True,
        help_text="The secret API key (auto-generated if left blank for API Key type)."
    )

    # --- Basic Auth Fields ---
    basic_auth_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username for HTTP Basic Authentication."
    )
    # Store HASHED password only!
    basic_auth_password_hash = models.CharField(
        max_length=128, # Store the hash (Django's default hash length)
        blank=True,
        null=True,
        help_text="Hashed password for HTTP Basic Authentication."
    )

    # --- Ownership and Timestamps ---
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # Or SET_NULL if preferred
        related_name='auth_profiles',
        help_text="The user who owns and manages this profile."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate fields based on auth_type."""
        super().clean()
        if self.auth_type == self.AuthType.API_KEY:
            if self.basic_auth_username or self.basic_auth_password_hash:
                raise ValidationError("Basic Auth username/password should not be set for API Key type.")
            # Key generation happens in save if needed
        elif self.auth_type == self.AuthType.BASIC:
            if self.api_key:
                raise ValidationError("API Key should not be set for Basic Auth type.")
            if not self.basic_auth_username:
                raise ValidationError("Basic Auth username is required for Basic Auth type.")
            # Password hash validation/presence is handled during save/form processing
        else:
            raise ValidationError("Invalid authentication type selected.") # Should not happen with choices

    def set_password(self, raw_password):
        """Hashes the raw password and stores it."""
        if not raw_password:
             raise ValueError("Password cannot be empty.")
        self.basic_auth_password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        """Checks if the raw password matches the stored hash."""
        if not self.basic_auth_password_hash:
            return False
        return check_password(raw_password, self.basic_auth_password_hash)

    def generate_api_key(self):
        """Generates a secure, unique API key."""
        # Loop to ensure uniqueness, though collision is highly unlikely with UUID4/secrets.token_urlsafe
        while True:
            # Using secrets.token_urlsafe is generally preferred for keys
            # Adjust length as needed (e.g., 40 characters yields 60 bytes)
            key = secrets.token_urlsafe(40)
            if not AuthenticationProfile.objects.filter(api_key=key).exists():
                 self.api_key = key
                 break
        # Alternative using UUID:
        # self.api_key = uuid.uuid4().hex

    def save(self, *args, **kwargs):
        # Generate API key if type is API_KEY and key is not set
        if self.auth_type == self.AuthType.API_KEY and not self.api_key:
            self.generate_api_key()

        # Clear incompatible fields before saving based on type
        if self.auth_type == self.AuthType.API_KEY:
            self.basic_auth_username = None
            self.basic_auth_password_hash = None
        elif self.auth_type == self.AuthType.BASIC:
            self.api_key = None
            # Ensure password hash is set if username is present (rely on form/view logic to call set_password)
            if self.basic_auth_username and not self.basic_auth_password_hash:
                 # This indicates an issue, maybe raise error or log,
                 # as password should have been set before save is called.
                 # For now, let validation handle this state if needed.
                 pass

        self.full_clean() # Run validation before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_auth_type_display()})"


class MockEndpoint(UserTrackedModel):
    path = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="The unique URL path fragment."
        )
    authentication = models.ForeignKey(
        AuthenticationProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="mock_endpoints", 
        help_text="Optional authentication applied to all methods for this path."
        )
    description = models.TextField(
        blank=True, 
        help_text="Optional description for this endpoint."
        )

    def clean(self):
        if self.path:
            self.path = '/'.join(filter(None, self.path.strip().split('/')))
            if not self.path:
                 raise ValidationError({'path': "Path cannot be empty or just slashes after normalization."})
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        auth_status = "Protected" if self.authentication else "Public"
        return f"/{self.path} - ({auth_status})"
    
    class Meta:
        verbose_name = "Mock Endpoint"
        verbose_name_plural = "Mock Endpoints"
        ordering = ['path']

class ResponseHandler(models.Model):
    endpoint = models.ForeignKey(
        MockEndpoint, 
        related_name='handlers', 
        on_delete=models.CASCADE, 
        help_text="The endpoint this handler belongs to."
        )
    http_method = models.CharField(
        max_length=10, 
        choices=[('GET', 'GET'), 
                 ('POST', 'POST'), 
                 ('PUT', 'PUT'), 
                 ('PATCH', 'PATCH'), 
                 ('DELETE', 'DELETE'), 
                 ('OPTIONS', 'OPTIONS'),
                 ('HEAD', 'HEAD')], 
        db_index=True,
        help_text="The HTTP method this handler responds to."
        )
    response_status_code = models.PositiveIntegerField(
        default=200, 
        help_text="The HTTP status code to return."
        )
    response_headers = models.JSONField(
        default=dict, 
        blank=True, 
        help_text='JSON object of response headers (e.g., {"Content-Type": "application/json"}).'
        )
    response_body = models.TextField(
        blank=True, 
        help_text="The raw response body (JSON, XML, plain text, etc.)."
        )
    description = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Optional description for this specific method handler."
        )
    
    # TODO add optional delay/timeout functionality

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        self.http_method = self.http_method.upper()
        if not isinstance(self.response_headers, dict):
             raise ValidationError({'response_headers': 'Headers must be a valid JSON object (dictionary).'})
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.http_method} handler for {self.endpoint}"

    class Meta:
        verbose_name = "Response Handler"
        verbose_name_plural = "Response Handlers"
        unique_together = ('endpoint', 'http_method') # This may change at some point
        ordering = ['endpoint__path', 'http_method'] # Order logically


class AuditLog(models.Model):
    """
    Immutable log of system events for auditing and compliance.
    Tracks CRUD operations, authentication events, and permission denials.
    """
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        READ = 'READ', 'Read'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        AUTH_FAILURE = 'AUTH_FAILURE', 'Authentication Failure'
        PERMISSION_DENIED = 'PERMISSION_DENIED', 'Permission Denied'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="The user who performed the action (null for anonymous)."
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        db_index=True,
        help_text="The type of action performed."
    )
    # Using IntegerField instead of ForeignKey so the ID persists after endpoint deletion
    endpoint_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="The ID of the endpoint involved (null for non-endpoint actions)."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred."
    )
    old_value = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON representation of the previous state (null for CREATE)."
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON representation of the new state (null for DELETE)."
    )

    def save(self, *args, **kwargs):
        # Prevent updates to existing records (immutability)
        if self.pk is not None:
            # Allow save but don't actually update - just return
            return
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion (immutability)
        return

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{self.action} by {username} at {self.timestamp}"

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['endpoint_id', 'action']),
        ]
