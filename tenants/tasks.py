import logging
from pathlib import Path

from celery import shared_task
from django.db import transaction

from tenants.models import AccountJob
from tenants.utils import ensure_local_ready_folder
from raw_data.views import run_account_job

logger = logging.getLogger(__name__)


@shared_task
def run_account_job_celery_task(accountjob_id):
    run_account_job(accountjob_id)
    
@shared_task
def scan_for_ready_files():
    logger.info("Starting scan_for_ready_files task")

    jobs = AccountJob.objects.all().order_by('account', 'order')

    for job in jobs:
        try:
            if job.auto_or_manual == 'manual':
                continue

            ready_folder = Path(ensure_local_ready_folder(job))

            if not ready_folder.exists():
                continue

            files = list(ready_folder.iterdir())
            if not files:
                continue

            logger.info(
                f"Processing AccountJob {job.pk} sequentially"
            )

            # RUN DIRECTLY (NOT async)
            run_account_job(job.pk)

        except Exception as e:
            logger.exception(f"Error scanning AccountJob {job.pk}: {e}")

    logger.info("Completed scan_for_ready_files task")
