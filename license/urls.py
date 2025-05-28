from django.urls import path

from .views import LicenseDetailView, LicenseUpdateView, sync_license

urlpatterns = [
    path("",             LicenseDetailView.as_view(), name="license_detail"),
    path("edit/",        LicenseUpdateView.as_view(), name="license_update"),
    path("sync/",        sync_license,                 name="license_sync"),
]
