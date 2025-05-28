from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class GroupObjectPermission(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    permission_type = models.CharField(max_length=50)  # 'view', 'edit', 'delete'
    
    # For linking to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        unique_together = ['group', 'permission_type', 'content_type', 'object_id']


class ExtendedGroup(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    # Add other fields as needed
    
    def __str__(self):
        return self.group.name


class User(AbstractUser):
    # Add any additional fields you might need
    # For example, you might want to add organization info, contact details, etc.
    is_admin = models.BooleanField(default=False)
    
    # For LDAP integration later
    is_ldap_user = models.BooleanField(default=False)
    ldap_dn = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        # Add permissions that will be used for escalated privileges
        permissions = [
            ("create_user", "Can create new users"),
            ("reset_user_password", "Can reset other users' passwords"),
            ("manage_user_groups", "Can manage user groups"),
        ]


class UserTrackedModel(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=False, 
        related_name="%(class)s_created"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,  # Optional as requested
        related_name="%(class)s_owned"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class ChangeLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)  # 'create', 'update', 'delete'
    changes = models.JSONField()  # Store the actual changes
    
    class Meta:
        ordering = ['-timestamp']