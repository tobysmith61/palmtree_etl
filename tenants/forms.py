# tenants/forms.py
from django import forms
from .models import Tenant, AccountTableData, SFTPDropZone
from canonical.widgets import PalmtreeExcelWidget #move to central
from django.conf import settings

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
            'data': PalmtreeExcelWidget(),  # editable
        }

class SFTPUploadForm(forms.Form):
    file = forms.FileField(label="Select a file to upload")

class SFTPDropZoneAdminForm(forms.ModelForm):

    class Meta:
        model = SFTPDropZone
        fields = "__all__"
        widgets = {
            "test_sftp_password": forms.PasswordInput(render_value=True),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        is_staging = getattr(settings, "IS_STAGING_SERVER", False)

        if not is_staging:
            self.fields.pop("test_sftp_user", None)
            self.fields.pop("test_sftp_password", None)
