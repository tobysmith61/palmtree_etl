from django.contrib import admin
from django.urls import path, include
#from rawdataeditor import views
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from tenants.views import home  # <-- updated
from tenants.views import TenantLogoutView

urlpatterns = [
    #path('', lambda request: redirect('/canonical/schema-overview/', permanent=True)),  #home

    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", TenantLogoutView.as_view(next_page="/"), name="logout"), #includes unsetting of session tenant_id
    path("tenants/", include("tenants.urls")),

    path('admin/', admin.site.urls),
    path('canonical/', include('canonical.urls')),
    path("contracts/", include("contracts.urls")),
    path("tenants/", include("tenants.urls")),
    

    
    
    #path('rawdataeditor/edit/<int:table_id>/', views.edit_table, name='edit_table'),
]
