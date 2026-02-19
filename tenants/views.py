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
from .models import Account, Tenant, UserAccount, AccountTableData, AccountJob
from .forms import TenantForm, SFTPUploadForm
from .utils import get_current_tenant

from canonical.widgets import ExcelWidget
from canonical.views import strip_empty_columns, strip_empty_rows, serialize_tabledata_for_widget, canonical_json_to_excel_style_table
from canonical.etl import run_etl_preview
from canonical.models import Job, FieldMapping

import paramiko
from django.contrib import messages


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
    print ("🆔 tenant.views dev_login_as session['account'] is now: "+str(account_id))

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

@require_POST
def admin_account_switch(request):
    account_id = request.POST.get("account_id")

    if account_id:
        request.session["account_id"] = int(account_id)
    else:
        request.session.pop("account_id", None)
    print ("🆔 tenant.views admin_account_switch session['account'] is now: "+str(account_id))

    #as we selected a different account, unset tenant,
    #forcing user to select another for the newly selected account
    request.session.pop("tenant_id", None)

    return redirect(request.META.get("HTTP_REFERER", "/admin/"))

def accountjob_preview(request, pk):
    accountjob = get_object_or_404(AccountJob, pk=pk)

    job = Job.objects.select_related(
        "canonical_schema",
        "source_schema",
        "test_table"
    ).get(pk=accountjob.job.pk)
    table_data = accountjob.account_table_data
    source_data = strip_empty_columns(strip_empty_rows(table_data.data or []))
    source_fields = job.source_schema.field_mappings.all()
    tenant_mapping = accountjob.tenant_mapping

    canonical_fields = job.canonical_schema.fields.all()
    canonical_rows, raw_json_rows, display_rows = run_etl_preview(
        source_fields=source_fields,
        canonical_fields=canonical_fields,
        table_data=table_data,
        tenant_mapping=tenant_mapping
    )

    canonical_table_data = canonical_json_to_excel_style_table(canonical_rows)
    display_table_data = canonical_json_to_excel_style_table(display_rows)
    table_widget = ExcelWidget(readonly=True)

    context = {
        "table_data": canonical_table_data,
        "table_source": table_widget.render("table_source", serialize_tabledata_for_widget(source_data)),
        "raw_json_rows": raw_json_rows,
        "table_target": table_widget.render("table_target", serialize_tabledata_for_widget(canonical_table_data)),
        "table_display": table_widget.render("table_display", serialize_tabledata_for_widget(display_table_data)),
    }

    return render(request, "canonical/table_preview.html", context)

def sftp_drop_dashboard_view(request):
    if request.method == "POST":
        form = SFTPUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            remote_path = os.path.join('/remote/folder', file.name)
            try:
                upload_to_sftp(file, remote_path)
                messages.success(request, f"{file.name} uploaded successfully!")
            except Exception as e:
                messages.error(request, f"Upload failed: {e}")
            return redirect('sftp-drop')
    else:
        form = SFTPUploadForm()

    return render(request, "tenants/sftp_drop.html", {"form": form})


def upload_to_sftp(file_obj, remote_path):
    """
    Uploads a file to an SFTP server using Paramiko.
    """
    host = settings.SFTP_HOST
    port = getattr(settings, 'SFTP_PORT', 22)
    username = settings.SFTP_USERNAME
    password = settings.SFTP_PASSWORD  # or use key authentication

    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Upload the file
    sftp.putfo(file_obj, remote_path)  # file_obj should be a file-like object

    sftp.close()
    transport.close()