def tenant_context(request):
    tenant = getattr(request, "current_tenant", None)
    user = request.user
    can_edit = False

    if tenant and user.is_authenticated:
        can_edit = user.is_superuser or user.has_perm("tenants.change_tenant")
        
    return {
        "tenant": tenant,
        "can_edit_tenant": can_edit
    }
