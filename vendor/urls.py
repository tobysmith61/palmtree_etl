from django.urls import path
from . import views

app_name = "vendor"

urlpatterns = [
    path("create_sftp_account_instructions/", views.create_sftp_account_instructions, name="create_sftp_account_instructions"),
]
