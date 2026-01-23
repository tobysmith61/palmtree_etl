# tenants/forms.py
from django import forms
from .models import Tenant

class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            "internal_tenant_code",
            "external_tenant_code",
            "desc",
        ]
