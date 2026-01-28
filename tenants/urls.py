from django.urls import path
from .views import whoami
from .views import TenantListView, TenantCreateView, TenantUpdateView, select_tenant

app_name = "tenants"

urlpatterns = [
    path("whoami/", whoami, name="whoami"),

    path("", TenantListView.as_view(), name="tenant_list"),
    path("new/", TenantCreateView.as_view(), name="tenant_create"),
    path("<uuid:pk>/edit/", TenantUpdateView.as_view(), name="tenant_edit"),
    path("select/", select_tenant, name="select_tenant"),
]
