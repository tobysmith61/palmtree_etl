from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import TenantGroup


@admin.register(TenantGroup)
class TenantGroupAdmin(DraggableMPTTAdmin):
    list_display = ("tree_actions", "indented_title")
    mptt_level_indent = 30
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        account_id = request.GET.get("account__id__exact")
        group_type = request.GET.get("group_type__exact")

        if account_id:
            qs = qs.filter(account_id=account_id)

        if group_type:
            qs = qs.filter(group_type=group_type)

        return qs
    
    list_filter = ("account", "group_type")
