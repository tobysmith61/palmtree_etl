from django.urls import path
from . import views

app_name = "canonical"

urlpatterns = [
    path("schema-overview/", views.schema_overview, name="schema_overview"),
    path('tabledata/<int:pk>/preview/', views.job_preview, name='job_preview'),
]
