from django.core.management.base import BaseCommand
from django.db import transaction
from tenants.models import SFTPDropZone
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

class Command(BaseCommand):
    help = "Provision missing SFTP credentials for SFTPDropZone records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be provisioned without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        dropzones = SFTPDropZone.objects.all()

        created_count = 0

        for dz in dropzones:
            if dz.sftp_user and dz.folder_path:
                continue

            self.stdout.write(
                self.style.WARNING(
                    f"Provisioning SFTP for DropZone id={dz.id} "
                    f"({dz.account.short}/{dz.zone_folder})"
                )
            )

            if dry_run:
                continue

            try:
                with transaction.atomic():
                    username, password = provision_sftp(dz)

                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created → username: {username} | password: {password}"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  Failed for DropZone id={dz.id}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created_count} SFTP accounts provisioned."
            )
        )

