from django import forms
from .models import TableData, CanonicalField
from .widgets import ExcelWidget
from django.core.exceptions import ValidationError
import json

class TableDataForm(forms.ModelForm):
    class Meta:
        model = TableData
        fields = ['name', 'source_schema', 'data']  # only model fields
        widgets = {
            'data': ExcelWidget(),  # editable
        }

ALLOWED_NORMALISATION_KEYS = {
    "trim",
    "null_if_empty",
    "lowercase",
    "uppercase",
    "date_format",
    "boolean_map",
    "tri_state_map",
    "trim_whitespace",
}

class CanonicalFieldForm(forms.ModelForm):
    normalisation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "style": (
                "font-family: monospace; white-space: pre;"
                "font-size: 8px;"
            ),
        }),
        help_text="JSON normalisation rules",
    )

    class Meta:
        model = CanonicalField
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk and self.instance.normalisation:
            self.initial["normalisation"] = json.dumps(
                self.instance.normalisation,
                indent=2,
                sort_keys=True,
            )

    def clean_normalisation(self):
        raw = self.cleaned_data["normalisation"]
        if not raw:
            return []

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

        # your existing validation logic here
        return data
