from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Account, Tenant, UserAccount, Location
from django.utils.html import format_html
from django.templatetags.static import static
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
import json
from django.contrib import admin
from sandbox.models import TenantGroup, TenantGroupType

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

from django.contrib import admin
from .models import Marque, Brand


@admin.register(Marque)
class MarqueAdmin(admin.ModelAdmin):
    list_display = ('name', 'short')
    search_fields = ('name', 'short')
    ordering = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'short', 'marque')
    list_filter = ('marque',)
    search_fields = ('name', 'short', 'marque__name')
    ordering = ('marque', 'name')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        account_id = request.session.get("account_id")
        if account_id:
            qs = qs.filter(id=account_id)
        return qs

@admin.register(Tenant)
class TenantAdmin(RedirectOnSaveAdmin):
    fields = (
        "rls_key",
        'account',
        'brand',
        'location',
        "desc",
        "internal_tenant_code",
        "external_tenant_code",
        #"group",
        'logo_path',
        'is_live',
    )
    
    list_display = (
        "desc",
        "internal_tenant_code",
        "external_tenant_code",
        #"group",
        "created_at",
        "updated_at",
        "logo_preview",
    )

    search_fields = (
        "internal_tenant_code",
        "external_tenant_code",
        #"group",
    )

    ordering = ("internal_tenant_code",)
    readonly_fields = ("rls_key", "logo_preview")  # logo_preview must be readonly

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        account_id = request.session.get("account_id")
        if account_id:
            qs = qs.filter(account_id=account_id)
        return qs

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
    extra = 1  # show 1 extra blank row

class UserAccountInline(admin.TabularInline):
    model = UserAccount
    extra = 1  # show 1 extra blank row

@admin.register(Account)
class AccountAdmin(RedirectOnSaveAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    change_form_template = "admin/tenants/account/change_form.html"
    readonly_fields = ("account_hierarchy",)
    inlines = [TenantInline, UserAccountInline] 

    fieldsets = (
        (None, {
            "fields": ("name", "short")
        }),
        ("Account Hierarchy", {
            "classes": ("collapse",),  # makes this section collapsible
            "fields": ("account_hierarchy",)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        account_id = request.session.get("account_id")
        if account_id:
            qs = qs.filter(id=account_id)
        return qs

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

        tree_data = build_account_organisational_tree(obj)
        tree_json = json.dumps(tree_data)

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