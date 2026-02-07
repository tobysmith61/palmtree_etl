from django.contrib import messages
from django.urls import path
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.conf import settings

import shutil
import csv
import datetime
import json
import os
import paramiko

from canonical.models import TableData


def simulate_testaccount(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST":
        shutil.move("/src/file", "/dst/file")
        messages.success(request, "Simulation complete")
        return redirect("/admin/")

    return render(
        request,
        "admin/tenants/simulate_testaccount.html",
    )

# 👇 this is the key part
def register_extra_admin_urls(admin_site):
    original_get_urls = admin_site.get_urls

    def get_urls():
        urls = original_get_urls()
        custom = [
            path(
                "tenants/testaccount/simulate/",
                admin_site.admin_view(simulate_testaccount),
                name="tenants_simulate_testaccount",
            )
        ]
        return custom + urls

    admin_site.get_urls = get_urls

def simulate_testaccount(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST":

        qs = TableData.objects.filter(name="Customer Vehicle test data")
        if not qs.exists():
            messages.error(request, "No matching data found")
            return redirect("/admin/")

        row = qs.first()
        json_data = row.data  # list-of-lists

        # 1️⃣ Prepare filename
        base_name = "Customer Vehicle test data".replace(" ", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}.csv"

        # 2️⃣ Create CSV locally
        TEMP_FILES_DIR = settings.TEMP_FILES_DIR
        os.makedirs(TEMP_FILES_DIR, exist_ok=True)
        filepath = os.path.join(TEMP_FILES_DIR, filename)

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for r in json_data:
                writer.writerow([c if c is not None else "" for c in r])

        # 3️⃣ SFTP upload
        SFTP_HOST = settings.SFTP_HOST
        print (80)
        print (SFTP_HOST)
        SFTP_USER = settings.SFTP_USER
        SFTP_REMOTE_DIR = settings.SFTP_REMOTE_DIR
        SFTP_PASSWORD = settings.SFTP_PASSWORD

        transport = paramiko.Transport((SFTP_HOST, 22))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_path = os.path.join(SFTP_REMOTE_DIR, filename)
        sftp.put(filepath, remote_path)

        sftp.close()
        transport.close()

        messages.success(request, f"CSV file generated and uploaded to SFTP: {remote_path}")
        return redirect("/admin/")

    # GET renders form
    return render(request, "admin/tenants/simulate_testaccount.html")
