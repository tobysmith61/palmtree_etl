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
from .services.sftp import provision_sftp
from .local_kms import generate_encrypted_dek

from canonical.models import TableData
from core.admin_mixins import SoftDeleteFKAdminMixin

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
class LocationAdmin(AccountScopedAdminMixin, admin.ModelAdmin):
    pass

@admin.register(Tenant)
class TenantAdmin(SoftDeleteFKAdminMixin, AccountScopedAdminMixin, RedirectOnSaveAdmin):
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
class AccountAdmin(RedirectOnSaveAdmin):
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
    def save_model(self, request, obj, form, change):
        if not change:
            dek, encrypted_dek = generate_encrypted_dek()
            obj.encrypted_dek = encrypted_dek
        super().save_model(request, obj, form, change)


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
class AccountJobAdmin(AccountScopedAdminMixin, admin.ModelAdmin):
    list_display = ('account', 'job', 'sftp_drop_zone', 'tenant_mapping')
    list_display_links = ("job",)
    fieldsets = (
        (None, {
            'fields':
                ('account', 'job', 'sftp_drop_zone', 'tenant_mapping', 'account_table_data'),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        #filter sftp_drop_zone
        if db_field.name == "sftp_drop_zone":
            account_id = request.session.get('account_id')

            if account_id:
                kwargs["queryset"] = SFTPDropZone.objects.filter(
                    account_id=account_id
                )
            else:
                kwargs["queryset"] = SFTPDropZone.objects.none()

        #filter tenant_mapping
        if db_field.name == "tenant_mapping":
            account_id = request.session.get('account_id')

            if account_id:
                kwargs["queryset"] = TenantMapping.objects.filter(
                    account_id=account_id
                )
            else:
                kwargs["queryset"] = TenantMapping.objects.none()

        #filter account_table_data
        if db_field.name == "account_table_data":
            account_id = request.session.get('account_id')

            if account_id:
                kwargs["queryset"] = AccountTableData.objects.filter(
                    account_id=account_id
                )
            else:
                kwargs["queryset"] = AccountTableData.objects.none()

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
class TenantMappingAdmin(AccountScopedAdminMixin, admin.ModelAdmin):
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
class SFTPDropZoneAdmin(AccountScopedAdminMixin, admin.ModelAdmin):
    readonly_fields = ('sftp_user', 'folder_path')
    fields = ('account', 'zone_folder', 'desc', 'sftp_user', 'folder_path', 'retention_period_days')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "_create_sftp" in request.POST:
            username, password = provision_sftp(obj)
            messages.success(
                request,
                f"SFTP created.\nUsername: {username}\nPassword: {password}"
            )


@admin.register(AccountTableData)
class AccountTableDataAdmin(AccountScopedAdminMixin, admin.ModelAdmin):
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
class JobAdmin(admin.ModelAdmin):
    pass
    