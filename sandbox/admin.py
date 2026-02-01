from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import TenantGroup


@admin.register(TenantGroup)
class TenantGroupAdmin(DraggableMPTTAdmin):
    list_display = ("tree_actions", "indented_title")
    mptt_level_indent = 30
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        #account_id = request.GET.get("account__id__exact")
        account_id = request.session.get("account_id")
       
        if account_id:
            qs = qs.filter(account_id=account_id)

        group_type = request.GET.get("group_type__exact")
        if group_type:
            qs = qs.filter(group_type=group_type)

        return qs
    
    list_filter = ("account", "group_type")
