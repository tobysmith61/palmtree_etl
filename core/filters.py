from django.contrib import admin
from tenants.models import Tenant

class TenantByAccountFilter(admin.SimpleListFilter):
    title = "tenant"
    parameter_name = "tenant"

    def lookups(self, request, model_admin):
        account_id = request.session.get("account_id")

        if not account_id:
            return []

        tenants = Tenant.objects.filter(account_id=account_id)

        return [(t.pk, str(t)) for t in tenants]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tenant_id=self.value())
        return queryset
    
