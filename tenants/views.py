# canonical/views.py

# Standard library
from uuid import UUID

# Django
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth import login, logout, get_user_model
from django.conf import settings
from django.http import Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

# Local app
from .models import Account, Tenant, UserAccount
from .forms import TenantForm
from .utils import get_current_tenant



def select_tenant(request):
    user = request.user

    if not user.is_authenticated:
        return None

    # Superusers: do nothing automatically
    if user.is_superuser:
        return None
    
    # Get the user's account (exactly 1)
    account = UserAccount.objects.get(user=user).account

    # Get all tenants linked to that account
    tenants = Tenant.objects.filter(account=account)

    if request.method == "POST":
        tenant_id = request.POST.get("tenant")
        request.session["tenant_id"] = tenant_id
        return redirect("home")

    return render(request, "tenants/select_tenant.html", {"tenants": tenants})

def no_tenant(request):
    return render(request, "tenants/no_tenant.html")

def whoami(request):
    tenant = get_current_tenant(request)
    if tenant:
        return HttpResponse(f"Tenant: {tenant.name}")
    return HttpResponse("No tenant set")

def home(request):
    tenant_desc = None
    tenant = None

    # Check if tenant_id exists in session
    tenant_id = request.session.get("tenant_id")
    print ("tenant id:")
    print (tenant_id)
    if tenant_id:
        try:
            tenant = Tenant.objects.get(rls_key=UUID(tenant_id))
            tenant_desc = tenant.desc
        except Tenant.DoesNotExist:
            tenant_desc = None

    can_edit = (
        request.user.is_superuser
        or request.user.has_perm("tenants.change_tenant")
    )

    return render(request, "home.html", {
        "tenant_desc": tenant_desc,
        "tenant": tenant,
        "can_edit_tenant": can_edit,
    })

class TenantListView(LoginRequiredMixin, ListView):
    model = Tenant
    template_name = "tenants/tenant_list.html"

class TenantCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    permission_required = "tenants.add_tenant"
    success_url = "/tenants/"

class TenantUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    permission_required = "tenants.change_tenant"
    success_url = "/tenants/"
    success_url = reverse_lazy("home")
    #fields = ["internal_tenant_code", "external_tenant_code", "desc"]
    template_name = "tenants/tenant_form.html"

    def get_object(self, queryset=None):
        tenant = super().get_object(queryset)

        # Superusers can edit any tenant
        if self.request.user.is_superuser:
            return tenant

        # Normal users: only their tenant
        current_tenant = self.request.current_tenant

        if tenant != current_tenant:
            raise PermissionDenied("You cannot edit this tenant")

        return tenant
    

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({
                "class": (
                    "block w-full rounded-md border border-gray-400 "
                    "bg-white px-3 py-0 text-sm "
                    "shadow-sm "
                    "focus:border-blue-600 focus:ring-2 focus:ring-blue-200 "
                    "hover:border-gray-500"
                )
            })
        return form

User = get_user_model()

def developer_quick_logins(view_func):
    def wrapped(request, *args, **kwargs):
        if not settings.DEVELOPER_QUICK_LOGIN_BUTTONS:
            raise Http404
        # if not request.user.is_superuser:
        #     raise Http404
        return view_func(request, *args, **kwargs)
    return wrapped

def get_first_tenant_for_user(user):
    return user.tenants.first()

#@developer_quick_logins
def dev_login_as(request, username, account_id=None):
#    if not request.user.is_superuser:
#        raise PermissionDenied

    custom_logout(request)
    user = get_object_or_404(User, username=username)
    login(request, user)

    # Determine the account to use
    if account_id:
        account = get_object_or_404(Account, id=account_id)
    else:
        # Pick first account linked to user
        user_account = UserAccount.objects.filter(user=user).first()
        account = user_account.account if user_account else None

    if account:
        request.session["account_id"] = account.id

    request.session["impersonating"] = True

    return redirect("/")

@csrf_protect
def custom_logout(request):
    """
    Logs out the user and clears any tenant/account session info.
    """
    # Clear tenant/account related session keys if present
    for key in ["tenant_id", "account_id", "impersonating"]:
        request.session.pop(key, None)

    # Log out the user
    logout(request)

    # Redirect to login page (or homepage)
    return redirect("/login/")
