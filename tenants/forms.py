# tenants/forms.py
from django import forms
from .models import Tenant, AccountTableData
from canonical.widgets import ExcelWidget #move to central

class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            "internal_tenant_code",
            "external_tenant_code",
            "desc",
        ]

class AccountTableDataForm(forms.ModelForm):
    class Meta:
        model = AccountTableData
        fields = ['name', 'data']  # only model fields
        widgets = {
            'data': ExcelWidget(),  # editable
        }
