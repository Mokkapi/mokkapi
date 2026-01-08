from django.db import models

import uuid

class License(models.Model):
    instance_id  = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    client_id    = models.CharField("Client ID", max_length=128, blank=True)
    admin_email  = models.EmailField("Support email", blank=True)

    def __str__(self):
        return f"License {self.instance_id}"

class LicenseStatus(models.Model):
    license                = models.OneToOneField(
        License,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="status",
    )
    is_commercial          = models.BooleanField(default=False)
    maintenance_valid      = models.BooleanField(default=False)
    maintenance_end_date   = models.DateField(null=True, blank=True)
    first_purchase_date    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Status for {self.license.instance_id}"
