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

# TODO add a XML based endpoint 
class MokkBaseJSON(UserTrackedModel):
    name = models.CharField(max_length=100, blank=True, null=True)
    path = models.CharField(
        max_length=255,
        unique=True,
        help_text="The URL path to map (e.g., 'some/unique/path'), Leading/trailing slashes are ignored.."
    )
    data = models.JSONField(
        help_text="The JSON object to be returned when this URL is requested."
    )
    # TODO add methods allowed on each endpoint
    # TODO create a post requirement for endpoints (ie submit this JSON, receive this JSON)
    """
    method = models.CharField(
        max_length=255,
        unique=False,
        default="GET",
        help_text="What methods can be used on this endpoint?"
    )
    """
    authentication = models.ForeignKey(
        AuthenticationProfile,
        on_delete=models.SET_NULL, # Endpoint becomes public if profile is deleted
        null=True,  # Allows endpoint to have no authentication
        blank=True, # Allows selecting "None" in forms/admin
        related_name='endpoints',
        help_text="Optional authentication profile required to access this endpoint."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """
        Normalize the path by stripping leading/trailing slashes
        and validate JSON data format if needed (though JSONField does basic validation).
        """
        super().clean() # Call parent's clean method first

        if self.path:
            # Normalize: remove leading/trailing slashes and collapse multiple slashes
            normalized_path = '/'.join(filter(None, self.path.strip().split('/')))
            if not normalized_path:
                 raise ValidationError({'path': "Path cannot be empty or just slashes."})
            self.path = normalized_path

        # Optional: Add custom JSON validation logic here if needed
        # For example, check if it's an object or follows a specific schema
        # if not isinstance(self.data, dict):
        #     raise ValidationError({'data': "JSON data must be an object (dictionary)."})


    def save(self, *args, **kwargs):
        """
        Ensure clean() is called before saving.
        """
        self.full_clean() # Calls clean() and other model validation
        super().save(*args, **kwargs)

    def __str__(self):
        # Display the normalized path
        auth_status = "Protected" if self.authentication else "Public"
        return f"/{self.path} - ({auth_status})" # Add leading slash for display consistency
    
    # TODO add edit permissions by user group

