from django import forms
from .models import TableData, CanonicalField, FieldMapping
from .widgets import ExcelWidget
from django.core.exceptions import ValidationError
import json
import re
import json
from django import forms

class TableDataForm(forms.ModelForm):
    class Meta:
        model = TableData
        fields = ['name', 'source_schema', 'data']
        widgets = {
            'data': ExcelWidget(),
        }

    def to_snake_case(self, value):
        value = value.strip()
        value = re.sub(r'[^\w\s]', '', value)      # remove special chars
        value = re.sub(r'\s+', '_', value)         # spaces → underscore
        value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value)  # camelCase → snake
        return value.lower()

    
    def clean_data(self):
        data = self.cleaned_data.get('data')

        if not data:
            raise forms.ValidationError("Data cannot be empty.")

        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format.")

        if not isinstance(data, list) or not data:
            raise forms.ValidationError("Data must contain at least one row.")

        # ---------------------------------
        # REMOVE FULLY EMPTY TRAILING COLUMNS
        # ---------------------------------
        # Transpose to inspect columns
        transposed = list(zip(*data))

        cleaned_columns = []
        for col in transposed:
            # Keep column if ANY cell has real content
            if any(cell not in ("", None) for cell in col):
                cleaned_columns.append(col)

        if not cleaned_columns:
            raise forms.ValidationError("All columns are empty.")

        # Transpose back to rows
        data = [list(row) for row in zip(*cleaned_columns)]

        # ---------------------------------
        # CLEAN HEADERS
        # ---------------------------------
        headers = data[0]
        cleaned_headers = []
        seen = set()

        for header in headers:
            if not header:
                raise forms.ValidationError("Header names cannot be empty.")

            snake = self.to_snake_case(str(header))

            if snake in seen:
                raise forms.ValidationError(
                    f"Duplicate header detected after normalization: '{snake}'"
                )

            seen.add(snake)
            cleaned_headers.append(snake)

        data[0] = cleaned_headers

        # ---------------------------------
        # REMOVE FULLY EMPTY ROWS (optional)
        # ---------------------------------
        cleaned_rows = [cleaned_headers]
        for row in data[1:]:
            if any(cell not in ("", None) for cell in row):
                cleaned_rows.append(row)

        return cleaned_rows

ALLOWED_NORMALISATION_KEYS = {
    "trim",
    "null_if_empty",
    "lowercase",
    "uppercase",
    "date_format",
    "boolean_map",
    "tri_state_map",
    "collapse_whitespace",
    "remove_whitespace",
}

class FieldMappingInlineForm(forms.ModelForm):
    normalisation = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "rows": 2,
            "style": (
                "font-family: monospace; white-space: pre;"
                "font-size: 8px;"
            ),
        }),
        help_text="JSON normalisation rules",
    )

    class Meta:
        model = FieldMapping
        fields = ("order", "source_field_name", "active", 
                  "is_tenant_mapping_source", "normalisation", "pii_requires_encryption", 
                  "pii_requires_fingerprint", "is_volatile")
    
    def __init__(self, *args, **kwargs):
        source_schema = kwargs.pop("source_schema", None)
        super().__init__(*args, **kwargs)

        # --- Source field: text input by default
        self.fields["source_field_name"].widget = forms.TextInput()
        if source_schema:
            tabledata = getattr(source_schema, "table_data", None)
            if tabledata and tabledata.data and isinstance(tabledata.data[0], list):
                header = tabledata.data[0]
                field_choices=[("", "— Select source field —")] + [(h, h) for h in header if h]
                self.fields["source_field_name"].widget = forms.Select(
                    choices=field_choices
                )


class CanonicalFieldForm(forms.ModelForm):
    normalisation = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "rows": 2,
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
