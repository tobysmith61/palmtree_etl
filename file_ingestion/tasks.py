from celery import shared_task
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .models import IngestedFile
import shutil

@shared_task(bind=True)
def process_file(self, src_path):
    print("start")
    src = Path(src_path).resolve()
    dest_dir = Path(settings.INGESTION_RECEIVED_DIR).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    obj, created = IngestedFile.objects.get_or_create(
        filename=src.name, defaults={"status": "pending"}
    )
    print(f"[DB] Logging file: {src.name}, created={created}", flush=True)

    try:
        shutil.move(str(src), str(dest))
        print(f"[ETL] Moved file: {src} → {dest}", flush=True)

        obj.status = "processed"
        obj.processed_at = timezone.now()
        obj.save()
        print(f"[DB] Updated record: {obj.filename}, status={obj.status}", flush=True)

        return f"File {src.name} processed"

    except Exception as e:
        print(f"[ERROR] Failed to process file {src}: {e}", flush=True)
        obj.status = "failed"
        obj.error = str(e)
        obj.save()
        raise
