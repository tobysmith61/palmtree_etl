from celery import shared_task
from tenants.models import AccountJob
from raw_data.views import run_account_job
from tenants.utils import ensure_local_sftp_drop_folder
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_account_job_task(accountjob_pk):
    logger.info(f"Running AccountJob {accountjob_pk}")
    run_account_job(accountjob_pk)


@shared_task
def scan_for_ready_files():
    for job in AccountJob.objects.select_related("tenant"):
        ready_folder = Path(ensure_local_sftp_drop_folder(job))
        if not ready_folder.exists():
            continue
        files = list(ready_folder.iterdir())
        if not files:
            continue
        run_account_job_task.delay(job.pk)
