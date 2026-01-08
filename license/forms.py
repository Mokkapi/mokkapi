from django import forms

from .models import License

class LicenseUpdateForm(forms.ModelForm):
    class Meta:
        model  = License
        fields = ["client_id", "admin_email"]
        widgets = {
            "client_id":   forms.TextInput(attrs={"placeholder": "Paste your purchased client ID"}),
            "admin_email": forms.EmailInput(attrs={"placeholder": "Support contact email"}),
        }
