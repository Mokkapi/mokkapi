from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from .models import ChangeLog, UserTrackedModel
from .middleware import get_current_user

@receiver(pre_save)
def track_changes(sender, instance, **kwargs):
    # Skip if not a UserTrackedModel or if it's our ChangeLog model
    if not isinstance(instance, UserTrackedModel) or sender == ChangeLog:
        return
    
    # Store original state if this is an update
    if instance.pk:
        try:
            instance._original_state = model_to_dict(sender.objects.get(pk=instance.pk))
        except sender.DoesNotExist:
            instance._original_state = {}
    else:
        instance._original_state = {}

@receiver(post_save)
def log_changes(sender, instance, created, **kwargs):
    # Skip if not a UserTrackedModel or if it's our ChangeLog model
    if not isinstance(instance, UserTrackedModel) or sender == ChangeLog:
        return
    
    # Get the current user from the request
    from django.contrib.auth.models import AnonymousUser
    from django.conf import settings
    
    user = get_current_user()
    if not user or user.is_anonymous:
        # Use a system user or just log without a user
        return
    
    if created:
        action = 'create'
        changes = model_to_dict(instance)
    else:
        action = 'update'
        current = model_to_dict(instance)
        original = getattr(instance, '_original_state', {})
        changes = {
            field: {'from': original.get(field), 'to': current.get(field)}
            for field in current
            if field in original and original.get(field) != current.get(field)
        }
    
    # Only log if there are changes
    if changes:
        ChangeLog.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(sender),
            object_id=instance.pk,
            action=action,
            changes=changes
        )

"""
@receiver(post_delete)
def log_deletion(sender, instance, deleted, **kwargs):
    # Skip if not a UserTrackedModel or if it's our ChangeLog model
    if not isinstance(instance, UserTrackedModel) or sender == ChangeLog:
        return
    # TODO update the following to correctly signal for deletion rather than creation
    from django.contrib.auth.models import AnonymousUser
    from django.conf import settings
    
    user = getattr(instance, '_user', None)
    if not user or isinstance(user, AnonymousUser):
        # Use a system user or just log without a user
        return
    
    if deleted:
        action = 'delete'
        changes = model_to_dict(instance)
    
    # Only log if there are changes
    if changes:
        ChangeLog.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(sender),
            object_id=instance.pk,
            action=action,
            changes=changes
        )
"""
