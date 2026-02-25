import os
import subprocess
from django.conf import settings
from django.utils.crypto import get_random_string


def provision_sftp(dropzone):
    base_path = getattr(settings, "SFTP_BASE_PATH", "/srv/sftp_drops")
    folder_path = f"{base_path}/{dropzone.account.short.lower()}/{dropzone.zone_folder}/drop"
    username = f"{dropzone.account.short}_{dropzone.zone_folder}".lower()
    password = get_random_string(16)

    os.makedirs(folder_path, exist_ok=True)

    subprocess.run(["sudo", "useradd", "-m", "-d", folder_path, "-s", "/usr/sbin/nologin", username], check=True)
    subprocess.run(["sudo", "chpasswd"], input=f"{username}:{password}".encode(), check=True)

    dropzone.folder_path = folder_path
    dropzone.sftp_user = username
    dropzone.save(update_fields=["folder_path", "sftp_user"])

    return username, password
