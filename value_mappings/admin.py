from django.contrib import admin
from .models import ValueMappingGroup, ValueMapping
from core.admin_mixins import SoftDeleteAdminMixin, TimeStampedAdminMixin, StagingReadOnlyAdminMixin


class ValueMappingInline(admin.TabularInline):
    model = ValueMapping
    extra = 1
    fields = ("from_code", "to_code")


@admin.register(ValueMappingGroup)
class ValueMappingGroupAdmin(
    SoftDeleteAdminMixin, 
    TimeStampedAdminMixin, 
    StagingReadOnlyAdminMixin, 
    admin.ModelAdmin
):
    list_display = ("code", "description")
    search_fields = ("code",)
    inlines = [ValueMappingInline]
