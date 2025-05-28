# license/signals.py
from django.db import OperationalError, DatabaseError
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import License

@receiver(post_migrate)
def ensure_license_exists(sender, **kwargs):
    if sender.name != "license":
        return

    try:
        if not License.objects.exists():
            License.objects.create()
    except (OperationalError, DatabaseError):
        # DB not ready or using a DB backend that can't handle it yet
        pass
