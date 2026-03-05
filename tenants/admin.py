from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.templatetags.static import static
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .admin_extra import register_extra_admin_urls
from .admin_mixins import AccountScopedAdminMixin, AccountScopedInlineMixin
from .forms import AccountTableDataForm
from .models import Account, Tenant, UserAccount, Location, AccountEncryption
from .models import TenantMapping, TenantMappingCode
from .models import AccountJob, SFTPDropZone, SFTPDropZoneScopedTenant, AccountTableData
from .local_kms import generate_encrypted_dek

from canonical.models import TableData
from core.admin_mixins import PalmTreeGenericAdminMixin

from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages

import os
import subprocess
from django.conf import settings
from django.utils.crypto import get_random_string



register_extra_admin_urls(admin.site)

User = get_user_model()

def logo_preview(self, obj):
    """Show a small preview of the tenant logo in admin"""
    if obj.logo_path:
        url = static(obj.logo_path)
        return format_html(
            '<div style="text-align:center;">'
            '<img src="{}" style="height:60px; object-fit:contain;" />'
            '</div>',
            url
        )
    return "-"

class RedirectOnSaveAdmin(admin.ModelAdmin):
    """
    Redirects to the `next` URL if provided after saving.
    """

    def response_add(self, request, obj, post_url_continue=None):
        next_url = request.GET.get("next")
        if next_url:
            return HttpResponseRedirect(next_url)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        next_url = request.GET.get("next")
        if next_url:
            return HttpResponseRedirect(next_url)
        return super().response_change(request, obj)


@admin.register(Location)
class LocationAdmin(
    AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin, 
):
    pass

@admin.register(Tenant)
class TenantAdmin(
    AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin, 
    RedirectOnSaveAdmin
):
    fields = (
        'rls_key',
        'account',
        'brand',
        'location',
        'desc',
        'internal_tenant_code',
        'external_tenant_code',
        'logo_path',
        'is_live',
    )
    
    list_display = (
        "desc",
        "internal_tenant_code",
        "external_tenant_code",
        "created_at",
        "updated_at",
        "logo_preview",
    )

    search_fields = (
        "internal_tenant_code",
        "external_tenant_code",
    )

    ordering = ("internal_tenant_code",)
    readonly_fields = ("rls_key", "logo_preview")  # logo_preview must be readonly

    def logo_preview(self, obj):
        """Show a small preview of the tenant logo in admin"""
        if obj.logo_path:
            url = static(obj.logo_path)
            return format_html(
                '<div style="text-align:center;">'
                '<img src="{}" style="height:60px; object-fit:contain;" />'
                '</div>',
                url
            )
        return "-"
TenantAdmin.logo_preview.short_description = "Logo"



class TenantInline(admin.TabularInline):
    model = Tenant
    classes = ['collapse'] 
    extra = 1  # show 1 extra blank row

class UserAccountInline(admin.TabularInline):
    model = UserAccount
    classes = ['collapse'] 
    extra = 1  # show 1 extra blank row

class SFTPDropZoneInline(AccountScopedInlineMixin, admin.TabularInline):
    model = SFTPDropZone
    extra = 1
    fields = ('zone_folder', 'desc', 'scope')
    show_change_link = True  # optional
    classes = ['collapse'] 

class AccountJobInline(AccountScopedInlineMixin, admin.TabularInline):
    model = AccountJob
    extra = 1
    fields = ('job', 'sftp_drop_zone', 'tenant_mapping')
    show_change_link = True  # optional
    classes = ['collapse'] 

@admin.register(Account)
class AccountAdmin(
    PalmTreeGenericAdminMixin, 
    RedirectOnSaveAdmin
):
    search_fields = ("name",)
    ordering = ("name",)
    change_form_template = "admin/tenants/account/change_form.html"
    readonly_fields = ("account_hierarchy",)
    inlines = [TenantInline, UserAccountInline, SFTPDropZoneInline, AccountJobInline] 

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        account_id = request.session.get('account_id')
        if account_id:
            return qs.filter(**{f"id": account_id})
        return qs

    fieldsets = (
        (None, {
            "fields": ("name", "short")
        }),
        ("ACCOUNT HIERARCHY", {
            "classes": ("collapse",),  # makes this section collapsible
            "fields": ("account_hierarchy",)
        }),
    )

    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/jstree@3.3.12/dist/themes/default/style.min.css",
                "tenants/css/jstree_admin.css",
            )
        }
        js = (
            "https://cdn.jsdelivr.net/npm/jstree@3.3.12/dist/jstree.min.js",
            "tenants/js/expand_fieldset.js",
        )

    def account_hierarchy(self, obj):
        if not obj.pk:
            return "Save account to view structure"

        #tree_data = build_account_organisational_tree(obj)
        tree_json = {}#json.dumps(tree_data)

        return format_html(
            """
            <div id="account-tree" style="margin-top: 10px;"></div>

            <script>
            (function() {{
                const data = {};

                function initTree() {{
                    const $ = django.jQuery;

                    const el = $('#account-tree');
                    if (!el.length) return;

                    el
                    .on('ready.jstree', function () {{
                        el.jstree('open_all');
                    }})
                    .jstree({{
                        core: {{
                            data: data,
                            themes: {{
                                dots: true,
                                icons: true
                            }}
                        }}
                    }});
                }}

                // Run after admin JS is ready
                if (document.readyState !== 'loading') {{
                    setTimeout(initTree, 50);
                }} else {{
                    document.addEventListener('DOMContentLoaded', function () {{
                        setTimeout(initTree, 50);
                    }});
                }}
            }})();
            </script>
            """,
            mark_safe(tree_json),
        )

    account_hierarchy.short_description = "Account Structure"

    # Pass info to template: disable dropdown on change/add pages
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["disable_account_dropdown"] = False
        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["disable_account_dropdown"] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["disable_account_dropdown"] = True
        return super().add_view(request, form_url, extra_context=extra_context)
    
def build_account_organisational_tree(account):
    return build_account_tree(account, TenantGroupType.OPERATING)

def build_account_tree(account,  group_type):
    roots = TenantGroup.objects.filter(
        account=account,
        group_type=group_type,
        parent__isnull=True,
    )
    
    def node_to_dict(node):
        return {
            "id": str(node.id),
            "text": str(node),
            "children": [
                node_to_dict(child)
                for child in node.get_children()
            ],
            "icon": "jstree-folder" if node.node_type != "tenant" else "jstree-file",
        }

    return [node_to_dict(root) for root in roots]

@admin.register(AccountJob)
class AccountJobAdmin(
    AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin, 
):
    list_display = ('account', 'job', 'sftp_drop_zone', 'tenant_mapping')
    list_display_links = ("job",)
    fieldsets = (
        (None, {
            'fields':
                ('account', 'job', 'sftp_drop_zone', 'tenant_mapping', 'account_table_data'),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Determine account_id
        account_id = None

        object_id = request.resolver_match.kwargs.get("object_id")
        if object_id:
            try:
                obj = self.model.objects.get(pk=object_id)
                account_id = obj.account_id
            except self.model.DoesNotExist:
                pass

        if not account_id:
            account_id = request.GET.get("account") or request.session.get("account_id")

        # Only filter relevant fields
        if db_field.name in ["sftp_drop_zone", "tenant_mapping", "account_table_data"]:
            qs = kwargs.get("queryset") or db_field.remote_field.model.objects.all()
            kwargs["queryset"] = qs.filter(account_id=account_id) if account_id else qs.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
class TenantMappingCodeInline(admin.TabularInline):
    model = TenantMappingCode
    extra = 1  # Number of extra blank rows
    fields = ('source_system_field_value', 'mapped_tenant', 'effective_from_date')
    show_change_link = True  # Allows clicking to edit in separate page if needed

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mapped_tenant":
            account_id = request.session.get('account_id')

            if account_id:
                kwargs["queryset"] = Tenant.objects.filter(
                    account_id=account_id
                )
            else:
                kwargs["queryset"] = Tenant.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(TenantMapping)
class TenantMappingAdmin(AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin
):
    list_display = ('account', 'desc')
    search_fields = ('account__name', 'desc')  # assuming Account has a name field
    inlines = [TenantMappingCodeInline]
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only restrict the tenant dropdown
        if db_field.name == "mapped_tenant":
            account_id = request.session.get('account_id')
            if account_id:
                kwargs["queryset"] = Tenant.objects.filter(account_id=account_id)
            else:
                # Optionally raise error if session has no account
                kwargs["queryset"] = Tenant.objects.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class SFTPDropZoneScopedTenantInline(admin.TabularInline):
    model = SFTPDropZoneScopedTenant
    extra = 1  # number of empty forms to show
    autocomplete_fields = ["scoped_tenant"]  # optional, if you have many tenants

@admin.register(SFTPDropZone)
class SFTPDropZoneAdmin(
    AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin, 
):
    readonly_fields = ('sftp_user', 'folder_path')
    fields = (
        'account',
        'zone_folder',
        'desc',
        'sftp_user',
        'folder_path',
        'retention_period_days'
    )

    def provision_sftp(self, dropzone):        
        base_path = getattr(settings, "SFTP_BASE_PATH", "/srv/sftp_drops")
        folder_path = f"{base_path}/{dropzone.account.short.lower()}/{dropzone.zone_folder}/drop"
        username = f"{dropzone.account.short}_{dropzone.zone_folder}".lower()
        password = get_random_string(16)

        os.makedirs(folder_path, exist_ok=True)

        subprocess.run(["sudo", "useradd", "-m", "-d", folder_path, "-s", "/usr/sbin/nologin", username], check=True)
        subprocess.run(["sudo", "chpasswd"], input=f"{username}:{password}".encode(), check=True)

        dropzone.folder_path = folder_path
        dropzone.sftp_user = username
        dropzone.save(update_fields=["folder_path", "sftp_user"])

        return username, password

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/provision-sftp/",
                self.admin_site.admin_view(self.provision_sftp_view),
                name="yourapp_sftpdropzone_provision_sftp",
            ),
        ]
        return custom_urls + urls

    def provision_sftp_view(self, request, object_id):    
        if getattr(settings, "IS_STAGING_SERVER", False):
            messages.warning(
                request,
                f"This action can only be performed on the live site!"
            )
            return redirect("..")
        
        obj = self.get_object(request, object_id)
        if not obj:
            messages.error(request, "Object not found.")
            return redirect("..")

        if obj.sftp_user:
            messages.warning(request, "SFTP already provisioned.")
            return redirect("..")

        username, password = self.provision_sftp(obj)

        messages.success(
            request,
            f"SFTP created — Username: {username} | Password: {password}"
        )

        return redirect("..")

@admin.register(AccountTableData)
class AccountTableDataAdmin(
    AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin, 
):
    form = AccountTableDataForm
    list_display = ('account', 'name', 'table_data_copied_from')
    change_form_template = "admin/tenants/accounttabledata/change_form.html"

    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.js',
        )

    fieldsets = (
        (None, {
            'fields': ('name', 'table_data_copied_from', 'data'),
        }),
    )

    # ─────────────────────────────
    # Custom admin URL
    # ─────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/clone-from-canonical/",
                self.admin_site.admin_view(self.clone_from_canonical),
                name="accounttabledata_clone_from_canonical",
            ),
        ]
        return custom_urls + urls

    # ─────────────────────────────
    # Clone handler
    # ─────────────────────────────
    def clone_from_canonical(self, request, object_id):
        obj = get_object_or_404(AccountTableData, pk=object_id)
        obj.data = obj.table_data_copied_from.data
        obj.save()

        self.message_user(
            request,
            f"Cloned data from canonical table '{obj.table_data_copied_from.name}'.",
            level=messages.SUCCESS,
        )

        return redirect(
            "admin:tenants_accounttabledata_change",
            object_id,
        )

    # ─────────────────────────────
    # Provide canonical tables to template
    # ─────────────────────────────
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["canonical_tabledata"] = TableData.objects.all()
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(AccountEncryption)
class AccountEncryptionAdmin(
    AccountScopedAdminMixin, 
    PalmTreeGenericAdminMixin,
): 
    fieldsets = (
        (None, {
            "fields": ("account", "dek_kms_key_id", "dek_algorithm",)
        }),
    )

    def save_model(self, request, obj, form, change):
        #############################
        # auto generate encrypted_dek
        #############################
        if not obj.encrypted_dek:
            dek, encrypted_dek = generate_encrypted_dek()
            obj.encrypted_dek = encrypted_dek
        super().save_model(request, obj, form, change)
