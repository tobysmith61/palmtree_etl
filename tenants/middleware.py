from django.shortcuts import redirect
from django.urls import reverse
from .utils import resolve_user_tenant, NoTenantError, MultipleTenantsError
from .models import Tenant

class TenantResolutionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/tenants/dev/login-as/"):
            return self.get_response(request)
        
        if request.user.is_authenticated:
            # Only resolve tenant if not already set in session
            tenant_id = request.session.get("tenant_id")
            if not tenant_id:
                try:
                    resolve_user_tenant(request)  # sets request.current_tenant & session
                except MultipleTenantsError:
                    # Redirect to the select tenant page
                    if request.path != reverse("tenants:select_tenant"):
                        return redirect("tenants:select_tenant")
                except NoTenantError:
                    # Redirect to a page informing user has no tenant
                    if request.path != reverse("tenants:no_tenant"):
                        return redirect("tenants:no_tenant")
            else:
                # If tenant_id in session, set request.current_tenant for convenience
                from .models import Tenant
                try:
                    request.current_tenant = Tenant.objects.get(pk=tenant_id)
                except Tenant.DoesNotExist:
                    # If tenant was deleted, clear session and redirect
                    del request.session["tenant_id"]
                    return redirect("tenants:select_tenant")

        response = self.get_response(request)
        return response
    