from pathlib import Path
import shutil
from celery import shared_task

DROP_FOLDER = Path("/srv/sftp_drops/voltaris/777/drop")
READY_FOLDER = Path("/srv/sftp_drops/voltaris/777/ready")
READY_FOLDER.mkdir(exist_ok=True)  # ensure folder exists

@shared_task
def promote_dropzone_files():
    for file_path in DROP_FOLDER.iterdir():
        if file_path.is_file():
            dst = READY_FOLDER / file_path.name
            shutil.copy2(file_path, dst)  # copy preserves metadata
            print(f"Copied {file_path.name} to ready")
