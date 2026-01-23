from django import forms
from .models import TableData, CanonicalField
from .widgets import ExcelWidget
from django.core.exceptions import ValidationError

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
    normalisation = forms.JSONField(
        required=False,
        help_text=(
            "Allowed ops:<br>"
            + "<br>".join(sorted(ALLOWED_NORMALISATION_KEYS))
            + "<br>Example: [{'op': 'trim'}, {'op': 'lowercase'}]"
        ),
        widget=forms.Textarea(attrs={"rows": 4, "cols": 40}),
    )

    class Meta:
        model = CanonicalField
        fields = "__all__"

    def clean_normalisation(self):
        data = self.cleaned_data.get("normalisation") or []

        if not isinstance(data, list):
            raise ValidationError("Normalisation must be a list")

        for i, step in enumerate(data):
            if not isinstance(step, dict):
                raise ValidationError(f"Step {i} must be an object")

            op = step.get("op")
            if not op:
                raise ValidationError(f"Step {i} missing 'op'")

            if op not in ALLOWED_NORMALISATION_KEYS:
                raise ValidationError(
                    f"Unknown normalisation op '{op}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_NORMALISATION_KEYS))}"
                )

        return data
