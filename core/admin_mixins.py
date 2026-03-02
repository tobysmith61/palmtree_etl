# admin_mixins.py
from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings


class SoftDeleteListFilter(admin.SimpleListFilter):
    title = "Active / Deleted Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("deleted", "Soft deleted"),
            ("all", "All (Active & Soft deleted)"),
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

class SoftDeleteFKAdminMixin:
    """
    Automatically filters ForeignKey dropdowns to exclude rows
    where 'deleted=True', for any related model that has a 'deleted' field.
    """

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        related_model = db_field.related_model
        if hasattr(related_model, "deleted"):
            # Only show non-deleted rows
            kwargs["queryset"] = related_model.objects.filter(deleted=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class TimeStampedAdminMixin:
    """
    Adds created_at and updated_at to list_display for any TimeStampedModel
    """
    def get_readonly_fields(self, request, obj=None):
        # Include parent readonly_fields
        fields = list(super().get_readonly_fields(request, obj))
        
        if hasattr(self.model, 'created_at') and 'created_at' not in fields:
            fields.append('created_at')
        if hasattr(self.model, 'updated_at') and 'updated_at' not in fields:
            fields.append('updated_at')
        
        return fields


class StagingReadOnlyAdminMixin:
    """
    Makes admin read-only when IS_STAGING_SERVER = True.
    """

    def is_readonly_environment(self):
        return not getattr(settings, "IS_STAGING_SERVER", False)

    def has_add_permission(self, request):
        if self.is_readonly_environment():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        if self.is_readonly_environment():
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        # Allow viewing in staging
        if self.is_readonly_environment():
            if request.method in ("GET", "HEAD"):
                return True
            return False
        return super().has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if self.is_readonly_environment():
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)
    
    def change_view(self, request, object_id, form_url="", extra_context=None):
        if self.is_readonly_environment():
            extra_context = extra_context or {}
            extra_context.update({
                "show_save": False,
                "show_save_and_continue": False,
                "show_save_and_add_another": False,
                "show_delete": False,
            })
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
    