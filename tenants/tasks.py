import logging
import os
import socket
import threading
from datetime import datetime
from pathlib import Path

from celery import shared_task
from tenants.models import AccountJob
from tenants.utils import ensure_local_ready_folder
from raw_data.views import run_account_job

logger = logging.getLogger(__name__)


def debug_context(prefix=""):
    return (
        f"{prefix} | "
        f"time={datetime.utcnow()} | "
        f"pid={os.getpid()} | "
        f"thread={threading.get_ident()} | "
        f"host={socket.gethostname()}"
    )


@shared_task(bind=True)
def scan_for_ready_files(self):
    logger.warning(debug_context("START scan_for_ready_files"))

    jobs = AccountJob.objects.all().order_by('account', 'order')

    for job in jobs:
        try:
            logger.warning(debug_context(f"CHECK job={job.pk}"))

            if job.auto_or_manual == 'manual':
                logger.warning(f"SKIP manual job={job.pk}")
                continue

            ready_folder = Path(ensure_local_ready_folder(job))

            if not ready_folder.exists():
                logger.warning(f"NO FOLDER job={job.pk}")
                continue

            files = list(ready_folder.iterdir())
            if not files:
                logger.warning(f"NO FILES job={job.pk}")
                continue

            logger.warning(debug_context(f"RUN START job={job.pk}"))

            # 🔴 CRITICAL: synchronous call
            run_account_job(job.pk)

            logger.warning(debug_context(f"RUN END job={job.pk}"))

        except Exception as e:
            logger.exception(f"ERROR job={job.pk}: {e}")

    logger.warning(debug_context("END scan_for_ready_files"))
    