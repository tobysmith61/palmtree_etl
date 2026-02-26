from django.urls import path
from .views import whoami
from .views import TenantListView, TenantCreateView, TenantUpdateView
from .views import select_tenant, dev_login_as, no_tenant, custom_logout, admin_account_switch
from .views import sftp_drop_dashboard_view, dropzone_files_api
from . import views

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
    path('accountjobpreview/<int:pk>/', views.accountjob_preview, name='accountjob_preview'),

    path('sftp-drop-dashboard/', sftp_drop_dashboard_view, name='sftp-drop-dashboard'),
    path('admin/dropzone-files/<int:pk>/', dropzone_files_api, name='dropzone_files_api'),
]
