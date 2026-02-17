from django.contrib import admin, messages
from django import forms
from django.utils.safestring import mark_safe
from django.apps import apps
from django.shortcuts import redirect, reverse
from django.db import models, transaction
from django.urls import path
from .forms import TableDataForm, CanonicalFieldForm
from .models import CanonicalSchema, CanonicalField, SourceSchema, FieldMapping, TableData, Job
from tenants.models import Tenant
import pandas as pd
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect


class CanonicalFieldInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        parent = self.instance
        if getattr(parent, "requires_tenant_mapping", False):
            tenant_code_fields = [
                form.cleaned_data
                for form in self.forms
                if not form.cleaned_data.get('DELETE', False)
                and form.cleaned_data.get('data_type') == "tenant_mapping"
            ]

            if len(tenant_code_fields) != 1:
                raise ValidationError(
                    "You must have exactly one CanonicalField with data_type='Tenant code mapping'."
                )
        
class CanonicalFieldInline(admin.TabularInline):
    model = CanonicalField
    extra = 1
    ordering = ("order",)
    fields = (
        "order",
        "name",
        "source_field",
        "data_type",
        "format_type",
        "value_mapping_group",
        "required",
        "normalisation",
    )
    form = CanonicalFieldForm
    show_change_link = True
    formset = CanonicalFieldInlineFormSet

@admin.register(CanonicalSchema)
class CanonicalSchemaAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "contract")
    search_fields = ("name", "description", "contract")
    inlines = [CanonicalFieldInline]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "description", "contract", "requires_tenant_mapping"),
            },
        ),
        (
            "Normalisation rules",
            {
                "classes": ("collapse",),
                "description": mark_safe(
                    """
                    <p><strong>Normalisation pipeline</strong></p>
                    <p>
                    Each field may define a normalisation pipeline as a JSON list.
                    Steps are applied in order.
                    </p>
                    <p><strong>Allowed ops:</strong></p>
                    <ul>
                        <li><code>trim</code></li>
                        <li><code>lowercase</code></li>
                        <li><code>uppercase</code></li>
                        <li><code>null_if_empty</code></li>
                        <li><code>date_format</code></li>
                        <li><code>boolean_map</code></li>
                        <li><code>tri_state_map</code></li>
                        <li><code>trim_whitespace</code></li>
                    </ul>
                    <p><strong>Example:</strong></p>
                    <pre>[{"op": "trim"}, {"op": "lowercase"}]</pre>
                    """
                ),
                "fields": (),
            },
        ),
    )

    # -----------------------------
    # Existing form with contract dropdown
    # -----------------------------
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "contract" in form.base_fields:
            contract_models = apps.get_app_config("contracts").get_models()

            choices = [
                (f"{model._meta.app_label}.{model.__name__}",
                 f"{model._meta.app_label}.{model.__name__}")
                for model in contract_models
            ]

            form.base_fields["contract"].widget = forms.Select(
                choices=[("", "---------")] + choices
            )

        return form

    # Make contract readonly once set
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.contract:
            return ("contract",)
        return ()


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/backfill_canonical_fields_from_canonical_contract/",
                self.admin_site.admin_view(self.backfill_canonical_fields_from_canonical_contract),
                name="backfill_canonical_fields_from_canonical_contract",
            ),
        ]
        return custom_urls + urls

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_backfill_canonical_fields_from_canonical_contract_button"] = True
        return super().changeform_view(request, object_id, form_url, extra_context)

    def backfill_canonical_fields_from_canonical_contract(self, request, pk):
        schema = self.get_object(request, pk)
        if not schema.contract:
            self.message_user(request, "No contract selected!", level=messages.ERROR)
            return redirect(reverse('admin:canonical_canonicalschema_change', args=[pk]))

        try:
            app_label, model_name = schema.contract.split(".")
            model = apps.get_model(app_label, model_name)
        except LookupError:
            self.message_user(request, f"Contract model {schema.contract} not found!", level=messages.ERROR)
            return redirect(reverse('admin:canonical_canonicalschema_change', args=[pk]))

        # Collect all fields from abstract bases
        abstract_fields = set()
        for base in model.__mro__:
            if hasattr(base, "_meta") and base._meta.abstract:
                abstract_fields.update(f.name for f in base._meta.fields)


        # Get business fields in order
        business_fields = [
            f for f in model._meta.fields
            if not f.auto_created
            and not getattr(f, "primary_key", False)
            and f.name not in abstract_fields
        ]


        # Map existing fields by uppercase name
        existing_fields = {cf.name.upper(): cf for cf in schema.fields.all()}

        new_count = 0
        renumber_count = 0

        for order, field in enumerate(business_fields, start=1):
            field_name_upper = field.name.upper()

            if field_name_upper in existing_fields:
                cf = existing_fields[field_name_upper]
                # Renumber if order mismatches
                if cf.order != order:
                    cf.order = order
                    cf.save(update_fields=["order"])
                    renumber_count += 1
            else:
                # Create new field
                CanonicalField.objects.create(
                    schema=schema,
                    name=field_name_upper,
                    data_type=self.map_model_field_to_data_type(field),
                    order=order
                )
                new_count += 1

        # Optionally, remove duplicates (rare case)
        duplicates = (
            schema.fields.values('name')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
        )
        for dup in duplicates:
            dups = list(schema.fields.filter(name=dup['name']).order_by('id'))
            for cf in dups[1:]:
                cf.delete()

        self.message_user(
            request,
            f"{new_count} new fields added, {renumber_count} fields renumbered to match contract model."
        )

        return redirect(reverse('admin:canonical_canonicalschema_change', args=[pk]))

    # -----------------------------
    # Add button to change form
    # -----------------------------
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_backfill_canonical_fields_from_canonical_contract_button"] = True
        extra_context["show_renumber_button"] = True
        return super().changeform_view(request, object_id, form_url, extra_context)

    # -----------------------------
    # Helper: map Django model field types to CanonicalField data_type
    # -----------------------------
    @staticmethod
    def map_model_field_to_data_type(field):
        from django.db import models as dj_models

        if isinstance(field, (dj_models.CharField, dj_models.TextField)):
            return "string"
        elif isinstance(field, dj_models.IntegerField):
            return "integer"
        elif isinstance(field, (dj_models.DateField, dj_models.DateTimeField)):
            return "date"
        elif isinstance(field, dj_models.BooleanField):
            return "boolean"
        elif isinstance(field, dj_models.EmailField):
            return "email"
        return "string"

class FieldMappingInlineForm(forms.ModelForm):
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

class FieldMappingInline(admin.TabularInline):
    model = FieldMapping
    form = FieldMappingInlineForm
    extra = 1  # allow adding new mappings

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)

        class InjectSourceSchemaFormSet(FormSet):
            def _construct_form(self, i, **form_kwargs):
                form_kwargs["source_schema"] = obj
                return super()._construct_form(i, **form_kwargs)

        return InjectSourceSchemaFormSet

@admin.register(SourceSchema)
class SourceSchemaAdmin(admin.ModelAdmin):
    inlines = [FieldMappingInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/backfill_source_fields_from_canonical_fields/",
                self.admin_site.admin_view(self.backfill_source_fields_from_canonical_fields),
                name="backfill_source_fields_from_canonical_fields",
            ),
        ]
        return custom_urls + urls

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_backfill_source_fields_from_canonical_fields_button"] = True
        return super().changeform_view(request, object_id, form_url, extra_context)

    def backfill_source_fields_from_canonical_fields(self, request, pk):
        source_schema = get_object_or_404(SourceSchema, pk=pk)

        canonical_schema = source_schema.canonical_schema
        if not canonical_schema:
            messages.error(request, "No canonical schema linked.")
            return redirect(request.path)

        canonical_fields = list(canonical_schema.fields.all())
        existing_mappings = {
            fm.canonical_field_id: fm
            for fm in source_schema.field_mappings.all()
        }

        updated = 0
        created = 0
        deactivated = 0

        with transaction.atomic():
            # 1️⃣ Ensure every canonical field has a mapping
            for canonical_field in canonical_fields:
                fm = existing_mappings.get(canonical_field.id)
                if fm:
                    # Update order & reactivate if needed
                    changed = False

                    if fm.order != canonical_field.order:
                        fm.order = canonical_field.order
                        changed = True

                    if not fm.active:
                        fm.active = True
                        changed = True

                    if changed:
                        fm.save(update_fields=["order", "active"])
                        updated += 1
                else:
                    print ('doesnt exists')
                    FieldMapping.objects.create(
                        source_schema=source_schema,
                        canonical_field=canonical_field,
                        source_field_name=None,
                        order=canonical_field.order,
                        active=True,
                        is_tenant_mapping_source=(
                            canonical_field.data_type == "tenant_mapping"
                        ),
                    )
                    created += 1

            # 2️⃣ Deactivate mappings whose canonical field no longer exists
            canonical_ids = {cf.id for cf in canonical_fields}

            removed_qs = source_schema.field_mappings.exclude(
                canonical_field_id__in=canonical_ids
            ).filter(active=True)

            deactivated = removed_qs.update(active=False)

            # 3️⃣ Renumber to ensure contiguous ordering
            mappings = list(
                source_schema.field_mappings
                .filter(active=True)
                .order_by("order", "id")
            )

            for idx, fm in enumerate(mappings, start=1):
                if fm.order != idx:
                    fm.order = idx
                    fm.save(update_fields=["order"])

        # 4️⃣ Feedback + refresh
        messages.success(
            request,
            f"Backfill complete: {created} created, {updated} updated, {deactivated} deactivated."
        )

        return redirect(
            reverse(
                "admin:canonical_sourceschema_change",
                args=[pk],
            )
        )

@admin.register(TableData)
class TableDataAdmin(admin.ModelAdmin):
    form = TableDataForm

    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.js',
        )
    fieldsets = (
        (None, {
            'fields': ('name', 'source_schema', 'data'),
        }),
    )

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    change_form_template = "admin/canonical/job/change_form.html"
    fields = ("desc", "source_schema", "canonical_schema", "test_table")
    