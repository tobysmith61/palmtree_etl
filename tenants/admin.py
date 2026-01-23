from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Tenant, UserTenant

User = get_user_model()

class UserTenantInline(admin.TabularInline):
    model = UserTenant
    extra = 1

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    fields = (
        "rls_key",  # top
        'desc',
        "internal_tenant_code",
        "external_tenant_code",
    )
    
    list_display = (
        'desc',
        "internal_tenant_code",
        "external_tenant_code",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "internal_tenant_code",
        "external_tenant_code",
    )

    readonly_fields = ("rls_key",)

    ordering = ("internal_tenant_code",)

admin.site.unregister(User)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    inlines = [UserTenantInline]
