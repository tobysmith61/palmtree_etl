from django.urls import path
from .views import whoami
from .views import TenantListView, TenantCreateView, TenantUpdateView
from .views import select_tenant, dev_login_as, no_tenant, custom_logout, admin_account_switch

app_name = "tenants"

urlpatterns = [
    path("whoami/", whoami, name="whoami"),

    path("", TenantListView.as_view(), name="tenant_list"),
    path("new/", TenantCreateView.as_view(), name="tenant_create"),
    path("<uuid:pk>/edit/", TenantUpdateView.as_view(), name="tenant_edit"),
    path("select/", select_tenant, name="select_tenant"),
    path("dev/login-as/<str:username>/", dev_login_as, name="dev_login_as"),
    path("no-tenant/", no_tenant, name="no_tenant"),

    path('logout/', custom_logout, name='logout'),

    path("admin/account-switch/", admin_account_switch, name="admin-account-switch"),

]
