from django.urls import path
from . import views

app_name = "contracts"

urlpatterns = [
    path("view/<str:model_name>/", views.model_contract_view, name="view"),
]
