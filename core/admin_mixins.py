# admin_mixins.py
from django.contrib import admin
from django.utils.html import format_html


class SoftDeleteListFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("deleted", "Deleted"),
            ("all", "All"),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == "deleted":
            return queryset.filter(deleted=True)

        if value == "all":
            return queryset

        # Default (active)
        return queryset.filter(deleted=False)
    
class SoftDeleteAdminMixin:

    def get_list_display(self, request):
        lst = super().get_list_display(request)
        if hasattr(self.model, 'deleted') and 'deleted_display' not in lst:
            lst = list(lst) + ['deleted_display']
        return lst

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))

        if hasattr(self.model, 'deleted'):
            filters.append(SoftDeleteListFilter)

        return filters

    def delete_model(self, request, obj):
        obj.deleted = True
        obj.save()

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def deleted_display(self, obj):
        if obj.deleted:
            return format_html('<span style="color:red;">&#10004;</span>')
        return ""

    deleted_display.short_description = "Deleted"
    deleted_display.admin_order_field = "deleted"
