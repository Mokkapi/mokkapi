# license/apps.py
from django.apps import AppConfig
from django.db.utils import OperationalError

class LicenseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "license"

    def ready(self):
        import license.signals
