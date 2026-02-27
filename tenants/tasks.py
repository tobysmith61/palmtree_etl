# tenants/tasks.py
from celery import shared_task
from pathlib import Path
from datetime import datetime, timedelta
from django.utils import timezone
from .models import SFTPDropZone

@shared_task
def promote_dropzone_files():
    """
    Move files from drop -> ready for all SFTPDropZones.
    """
    for dz in SFTPDropZone.objects.all():
        base = Path(dz.folder_path)
        drop = base / "drop"
        ready = base / "ready"
        ready.mkdir(exist_ok=True)

        # Move files atomically
        for f in drop.iterdir():
            if f.is_file() and not f.name.endswith(".tmp"):
                target = ready / f.name
                f.rename(target)

        # Optional: remove old files in ready/ past retention
        cutoff = timezone.now() - timedelta(days=dz.retention_period_days)
        for f in ready.iterdir():
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()