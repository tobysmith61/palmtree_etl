from django.contrib import admin
from .models import ValueMappingGroup, ValueMapping


class ValueMappingInline(admin.TabularInline):
    model = ValueMapping
    extra = 1
    fields = ("from_code", "to_code")


@admin.register(ValueMappingGroup)
class ValueMappingGroupAdmin(admin.ModelAdmin):#toby
    list_display = ("code", "description")
    search_fields = ("code",)
    inlines = [ValueMappingInline]
