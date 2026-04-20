from django.contrib import admin
from django.utils.html import format_html
import json
from .models import RawCustomerVehicleData, RawRecallData, RawBookingData
from core.filters import TenantByAccountFilter


class BaseRawDataAdmin(admin.ModelAdmin):
    fields = (
        "business_key_hash",
        "pretty_debug_business_key",
        "row_hash",
        "is_current",
        "processed",
        "ingested_at",
        "pretty_payload",
        "source_file",
        "source_row_number",
        "is_deleted_at_source",
    )

    readonly_fields = fields

    list_display = (
        "source_row_number",
        "is_current",
        "processed",
        "ingested_at",
        "is_deleted_at_source",
    )

    list_filter = (
        "is_current",
        "processed",
        "ingested_at",
        "is_deleted_at_source",
    )

    search_fields = ("source_file",)

    ordering = ("-ingested_at",)

    def pretty_payload(self, obj):
        if not obj.payload:
            return ""

        formatted_json = json.dumps(obj.payload, indent=2, sort_keys=True)

        return format_html(
            "<pre style='white-space: pre-wrap; word-wrap: break-word;'>{}</pre>",
            formatted_json,
        )

    pretty_payload.short_description = "Payload"

    def pretty_debug_business_key(self, obj):
        if not obj.debug_business_key:
            return ""

        formatted_json = json.dumps(obj.debug_business_key, indent=2, sort_keys=True)
        
        return format_html(
            "<pre style='white-space: pre-wrap; word-wrap: break-word;'>{}</pre>",
            formatted_json,
        )

    pretty_debug_business_key.short_description = "Debug business key"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

class TenantRawDataAdmin(BaseRawDataAdmin):
    fields = ("tenant",) + BaseRawDataAdmin.fields

    readonly_fields = fields

    list_display = ("tenant",) + BaseRawDataAdmin.list_display

    list_filter = (TenantByAccountFilter,) + BaseRawDataAdmin.list_filter

@admin.register(RawCustomerVehicleData)
class RawCustomerVehicleDataAdmin(TenantRawDataAdmin):
    pass

@admin.register(RawRecallData)
class RawRecallDataAdmin(BaseRawDataAdmin):
    pass


@admin.register(RawBookingData)
class RawBookingDataAdmin(TenantRawDataAdmin):
    pass
