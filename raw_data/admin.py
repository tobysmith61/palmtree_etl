from django.contrib import admin
from django.utils.html import format_html
import json
from .models import RawCustomerVehicleData
from core.filters import TenantByAccountFilter


@admin.register(RawCustomerVehicleData)
class RawCustomerVehicleDataAdmin(admin.ModelAdmin):
    # Fields shown in the detail/change view
    fields = (
        "tenant",
        "business_key_hash",
        "row_hash",
        "is_current",
        "processed",
        "ingested_at",
        "pretty_payload",
        "source_file",
        "source_row_number",
    )

    # Make everything read-only
    readonly_fields = fields

    list_display = (
        "tenant",
        "source_row_number",
        "is_current",
        "processed",
        "ingested_at",
    )

    list_filter = (
        TenantByAccountFilter,
        "is_current",
        "processed",
        "ingested_at",
    )

    search_fields = (
        "source_file",
    )

    ordering = ("-ingested_at",)

    # --------------------------
    # Custom display methods
    # --------------------------
    def pretty_payload(self, obj):
        """Show JSON payload pretty-printed in the admin."""
        if not obj.payload:
            return ""
        formatted_json = json.dumps(obj.payload, indent=2, sort_keys=True)
        return format_html(
            "<pre style='white-space: pre-wrap; word-wrap: break-word;'>{}</pre>",
            formatted_json
        )
    pretty_payload.short_description = "Payload"

    # --------------------------
    # Prevent adding or deleting
    # --------------------------
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    