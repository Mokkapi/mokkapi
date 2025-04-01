from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from user_management.models import UserTrackedModel

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
        return f"/{self.path}" # Add leading slash for display consistency
    
    # TODO add edit permissions by user group
