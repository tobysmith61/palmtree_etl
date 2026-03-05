from django.urls import path
from . import views
from .views import hot_demo

app_name = "canonical"

urlpatterns = [
    path("schema-overview/", views.schema_overview, name="schema_overview"),
    path('tabledata/<int:job_pk>/preview/', views.job_preview, name='job_preview'),
    path("hot-demo/", hot_demo, name="hot_demo"),
]
