from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView

import requests

from .forms  import LicenseUpdateForm
from .models import License, LicenseStatus

class LicenseDetailView(DetailView):
    model               = License
    template_name       = "license/license_detail.html"
    context_object_name = "license"

class LicenseUpdateView(UpdateView):
    model         = License
    form_class    = LicenseUpdateForm
    template_name = "license/license_update.html"
    success_url   = reverse_lazy("license_detail")

@staff_member_required
def sync_license(request):
    """
    Trigger a call to your central license server.
    Expects JSON response like:
    {
      "is_commercial": true,
      "maintenance_valid": true,
      "maintenance_end_date": "2025-12-31",
      "first_purchase_date": "2024-11-01T14:22:00Z"
    }
    """
    lic = get_object_or_404(License)
    payload = {
        "instance_id": str(lic.instance_id),
        "client_id":   lic.client_id,
    }

    try:
        resp = requests.post(
            "https://your-license-server.example.com/api/activate/",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        LicenseStatus.objects.update_or_create(
            license=lic,
            defaults={
                "is_commercial":        data.get("is_commercial", False),
                "maintenance_valid":    data.get("maintenance_valid", False),
                "maintenance_end_date": data.get("maintenance_end_date"),
                "first_purchase_date":  data.get("first_purchase_date"),
            },
        )
        messages.success(request, "License status synced successfully.")
    except Exception as e:
        messages.error(request, f"Failed to sync license: {e}")

    return redirect("license_detail")
