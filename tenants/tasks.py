import logging
import os
import socket
import threading
import time
import shutil

from datetime import datetime
from pathlib import Path

from celery import shared_task
from tenants.models import AccountJob
from tenants.utils import ensure_local_ready_folder

logger = logging.getLogger(__name__)


# =====================================================
# DEBUG HELPERS
# =====================================================

def debug_context(prefix=""):
    return (
        f"{prefix} | "
        f"time={datetime.utcnow()} | "
        f"pid={os.getpid()} | "
        f"thread={threading.get_ident()} | "
        f"host={socket.gethostname()}"
    )


# =====================================================
# SHARED CONFIG
# =====================================================

BASE_FOLDER = Path("/srv/sftp_drops")
READY_FOLDER_NAME = "ready"
CHECK_STABLE_SECONDS = 5


# =====================================================
# STAGE 1: DROP → READY
# =====================================================

def is_stable(file_path: Path) -> bool:
    """
    Simple stability check (no threads, no watchdog).
    """
    try:
        size1 = file_path.stat().st_size
        time.sleep(CHECK_STABLE_SECONDS)
        size2 = file_path.stat().st_size
        return size1 == size2
    except FileNotFoundError:
        return False


def promote_to_ready(file_path: Path):
    """
    Move file from drop → ready folder.
    """
    ready_folder = file_path.parent.parent / READY_FOLDER_NAME
    ready_folder.mkdir(exist_ok=True)

    destination = ready_folder / file_path.name
    shutil.move(str(file_path), str(destination))

    logger.warning(f"MOVED: {file_path} → {destination}")


@shared_task
def scan_dropzones():
    """
    Celery Beat task:
    Moves stable files from drop → ready
    """

    if not BASE_FOLDER.exists():
        logger.warning("BASE_FOLDER missing")
        return

    for drop_folder in BASE_FOLDER.rglob("drop"):
        for file_path in drop_folder.iterdir():

            if not file_path.is_file():
                continue

            if not is_stable(file_path):
                continue

            promote_to_ready(file_path)


# =====================================================
# STAGE 2: READY → PROCESSING
# =====================================================

@shared_task(bind=True)
def run_account_job_celery_task(self, accountjob_id):
    """
    Actual job execution (isolated worker task)
    """
    from raw_data.views import run_account_job

    logger.warning(f"START JOB {accountjob_id}")
    run_account_job(accountjob_id)
    logger.warning(f"END JOB {accountjob_id}")


@shared_task
def scan_for_ready_files():
    """
    Celery Beat task:
    Scans ready folders and queues processing jobs
    """

    jobs = AccountJob.objects.all().order_by("account", "order")

    for job in jobs:
        try:
            if job.auto_or_manual == "manual":
                continue

            ready_folder = Path(ensure_local_ready_folder(job))

            if not ready_folder.exists():
                continue

            files = [
                f for f in ready_folder.iterdir()
                if f.is_file() and f.name.startswith(job.job.source_schema.filename_prefix)
            ]
            if not files:
                continue

            logger.warning(f"QUEUE JOB {job.pk} | files={len(files)}")

            # IMPORTANT: async execution
            run_account_job_celery_task.delay(job.pk)

        except Exception as e:
            logger.exception(f"ERROR job={job.pk}: {e}")

