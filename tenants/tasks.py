from pathlib import Path
import shutil
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

BASE_FOLDER = Path("/srv/sftp_drops")
READY_FOLDER_NAME = "ready"

@shared_task
def promote_dropzone_files():
    """
    Recursively walk through all subfolders of BASE_FOLDER.
    For every file in a 'drop' folder, copy it to the corresponding 'ready' folder
    and delete the original after successful copy.
    """
    for drop_folder in BASE_FOLDER.rglob("drop"):
        if drop_folder.is_dir():
            # Determine corresponding READY folder
            ready_folder = drop_folder.parent / READY_FOLDER_NAME
            ready_folder.mkdir(exist_ok=True)
            
            for file_path in drop_folder.iterdir():
                if file_path.is_file():
                    dst = ready_folder / file_path.name
                    try:
                        shutil.copy2(file_path, dst)
                        logger.info(f"Copied {file_path} → {dst}")
                        file_path.unlink()
                        logger.info(f"Deleted original {file_path}")
                    except Exception as e:
                        logger.exception(f"Failed to promote {file_path}")
                        