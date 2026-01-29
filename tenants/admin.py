from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Account, Tenant, UserAccount, TenantGroupType #TenantGroup
from django.utils.html import format_html
from django.templatetags.static import static
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
import json
from django.urls import reverse
from django.contrib import admin
print (11)
print(admin.site)




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
    
@admin.register(Tenant)
class TenantAdmin(RedirectOnSaveAdmin):
    fields = (
        "rls_key",
        'account',
        "desc",
        "internal_tenant_code",
        "external_tenant_code",
        #"group",
        'logo_path',
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

from mptt.admin import DraggableMPTTAdmin

# if admin.site.is_registered(TenantGroup):
#     admin.site.unregister(TenantGroup)
# @admin.register(TenantGroup)

# class TenantGroupAdmin(DraggableMPTTAdmin):
#     mptt_indent_field = "name"
#     list_display = ("tree_actions", "indented_title", "account", "group_type")
#     list_display_links = ("indented_title",)
#     list_filter = ("account", "group_type")

#     def changelist_view(self, request, extra_context=None):
#         print("🔥 DRAGGABLE MPTT ADMIN ACTIVE 🔥")
#         return super().changelist_view(request, extra_context)

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
            "fields": ("name",)
        }),
        ("Account Hierarchy", {
            "classes": ("collapse",),  # makes this section collapsible
            "fields": ("account_hierarchy",)
        }),
    )

    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/jstree@3.3.12/dist/themes/default/style.min.css",
            )
        }
        js = (
            "https://cdn.jsdelivr.net/npm/jstree@3.3.12/dist/jstree.min.js",
            "tenants/js/expand_fieldset.js",
        )

    def account_hierarchy(self, obj):
        if not obj:
            return "Save account to view structure"

        tree_data = build_account_tree(obj)

        # edit_url = reverse(
        #         "admin:tenants_group_changelist"
        #     ) + f"?account__id__exact={obj.id}&_popup=1"
        return mark_safe("<div/>")
        return mark_safe(f"""
                         
            <div style="display:flex; align-items:center; gap:8px;">
                <strong>Account Structure</strong>
                <a href="{edit_url}" class="edit-popup-link" title="Edit groups">✏️</a>
            </div>

            <div id="account-tree"></div>

            <script>
                (function($) {{
                    $('#account-tree').jstree({{
                        core: {{
                            data: {json.dumps(tree_data)},
                            check_callback: false,
                            themes: {{ icons: true }}
                        }}
                    }}).on('ready.jstree', function () {{
                        $('#account-tree').jstree('open_all');
                    }});

                    // Popup for pencil icon
                    $('.edit-popup-link').on('click', function(e){{
                        e.preventDefault();
                        var url = $(this).attr('href');
                        window.open(url, "_blank", "height=600,width=1000,resizable=yes,scrollbars=yes");
                    }});
                }})(django.jQuery);
            </script>
        """)
    account_hierarchy.short_description = "Account Structure"



def build_account_tree(account):
    groups = (
        #TenantGroup.objects
        #.filter(account=account)
        #.prefetch_related("children")
    )

    tenants = Tenant.objects.filter(account=account)

    # Map tenants by group
    tenants_by_group = {}
    ungrouped_tenants = []

    for tenant in tenants:
        if tenant.group_id:
            tenants_by_group.setdefault(tenant.group_id, []).append(tenant)
        else:
            ungrouped_tenants.append(tenant)

    def tenant_node(tenant):
        return {
            "text": f"{tenant.internal_tenant_code} — {tenant.desc}",
            "icon": "🏷️",
            "state": {"opened": True},
        }

    def group_node(group):
        #icon = TenantGroupType(group.group_type).icon if group.group_type else "📁"

        return {
            "text": f"{icon} {group.name}",
            "icon": "folder",
            "state": {"opened": True},
            "children": (
                [group_node(child) for child in group.children.all()] +
                [tenant_node(t) for t in tenants_by_group.get(group.id, [])]
            ),
        }

    root_groups = [g for g in groups if g.parent_id is None]

    return [{
        "text": f"💼 {account.name}",
        "state": {"opened": True},
        "children": (
            [group_node(g) for g in root_groups] +
            ([{
                "text": "📦 Ungrouped Tenants",
                "state": {"opened": True},
                "children": [tenant_node(t) for t in ungrouped_tenants],
            }] if ungrouped_tenants else [])
        ),
    }]
