from .models import Tenant

class NoTenantError(Exception):
    pass


class MultipleTenantsError(Exception):
    pass


def resolve_user_tenant(request):
    """
    Determines tenant for the logged-in user.
    May set request.session["tenant_id"].
    """
    user = request.user

    if not user.is_authenticated:
        return None

    # Superusers: do nothing automatically
    if user.is_superuser:
        return None

    tenants = Tenant.objects.filter(usertenant__user=user).distinct()
    if tenants.count() == 0:
        raise NoTenantError("User has no tenants")

    if tenants.count() == 1:
        tenant = tenants.first()
        request.session["tenant_id"] = str(tenant.rls_key)
        return tenant

    # More than one → user must choose
    raise MultipleTenantsError("User has multiple tenants")

def get_current_tenant(request):
    tenant_id = request.session.get("tenant_id")
    if tenant_id:
        return Tenant.objects.get(rls_key=tenant_id)
    return None
