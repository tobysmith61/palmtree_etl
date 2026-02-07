from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import TenantGroup
from tenants.models import Tenant
from tenants.admin_mixins import AccountScopedAdminMixin

@admin.register(TenantGroup)
class TenantGroupAdmin(AccountScopedAdminMixin, DraggableMPTTAdmin):
    list_display = ('root_label', 'tree_actions', 'indented_title', 'tenant')
    mptt_level_indent = 30
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        group_type = request.GET.get("group_type__exact")
        if group_type:
            qs = qs.filter(group_type=group_type)

        return qs
    
    list_filter = ("account", "group_type")
    
    def get_fields(self, request, obj=None):
        fields = [
            'group_type',
            'root_label',
            'parent',
            'group_label',
            'node_type',
            'tenant',
        ]
        
        if obj or not request.session.get("account_id"):
            fields = ["account"] + fields
        return fields

    def get_changeform_initial_data(self, request):
        """
        Called when adding a new object via admin.
        Use request.GET to read filter values and default fields.
        """
        
        initial = super().get_changeform_initial_data(request)

        # Check for filter applied in admin to determine default value for group type
        group_type = None
        _changelist_filters = request.GET.getlist("_changelist_filters")
        for f in _changelist_filters:
            if f.startswith("group_type__exact="):
                group_type = f.split("=", 1)[1]  # get the value after '='
                break
        if group_type:
            initial["group_type"] = group_type
        return initial
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            qs = TenantGroup.objects.all()

            # Filter by session account
            account_id = request.session.get("account_id")
            if account_id:
                qs = qs.filter(account_id=account_id)

            # Filter by current group_type filter (if present)
            _filters = request.GET.getlist("_changelist_filters")
            for f in _filters:
                if f.startswith("group_type__exact="):
                    group_type = f.split("=", 1)[1]
                    qs = qs.filter(group_type=group_type)
                    break

            kwargs["queryset"] = qs

        # Only restrict the tenant dropdown
        if db_field.name == "tenant":
            account_id = request.session.get("account_id")
            if account_id:
                kwargs["queryset"] = Tenant.objects.filter(account_id=account_id)
            else:
                # Optionally raise error if session has no account
                kwargs["queryset"] = Tenant.objects.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

