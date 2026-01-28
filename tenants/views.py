# canonical/views.py
from django.shortcuts import render, redirect
from .models import Tenant, UserAccount
from .utils import get_current_tenant
from django.http import HttpResponse
from uuid import UUID
from django.contrib.auth.views import LogoutView
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.templatetags.static import static

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
    return render(request, "no_tenant.html", status=403)

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


class TenantLogoutView(LogoutView):
    next_page = "/"

    def dispatch(self, request, *args, **kwargs):
        # Remove tenant from session BEFORE logout
        request.session.pop("tenant_id", None)
        return super().dispatch(request, *args, **kwargs)
    
# tenants/views.py
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Tenant
from .forms import TenantForm

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
    

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Account, Group, Tenant

@staff_member_required
def account_tree(request):
    """
    Return the Account → Group → Tenant hierarchy as JSON for the tree view.
    Only accessible to staff (admin) users.
    """
    tree = []

    account_id = request.GET.get("account_id")
    
    account = Account.objects.get(pk=account_id)
    account_node = {
        "id": f"account-{account.id}",
        "title": 'Account: '+account.name,
        "type": "account",
        "url": f"/admin/tenants/account/{account.id}/change/",
        "icon": static('core/images/groupings/rooftop.jpg'),
        "children": []
    }

    groups = Group.objects.filter(account=account)
    for group in groups:
        group_node = {
            "id": f"group-{group.id}",
            "title": 'Group: '+group.name,
            "type": "group",
            "url": f"/admin/tenants/group/{group.id}/change/",
            "icon": static('core/images/groupings/rooftop.jpg'),
            "children": []
        }

        tenants = Tenant.objects.filter(group=group)
        for tenant in tenants:
            tenant_node = {
                "id": f"tenant-{tenant.pk}",
                "title": 'Tenant: '+tenant.desc,  # adjust if your tenant uses a different field
                "type": "tenant",
                "url": f"/admin/tenants/tenant/{tenant.pk}/change/",
                "icon": static(tenant.logo_path) if tenant.logo_path else None,
                "children": []
            }
            group_node["children"].append(tenant_node)

        account_node["children"].append(group_node)

        tree.append(account_node)

    return JsonResponse(tree, safe=False)



@staff_member_required
def account_tree_page(request):
    """
    Renders the interactive tree page
    """
    return render(request, "tenants/account_tree.html")