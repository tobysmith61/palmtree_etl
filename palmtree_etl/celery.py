import os
from celery import Celery
from celery.schedules import crontab
import tenants.tasks

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palmtree_etl.settings")

app = Celery("palmtree_etl")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "scan_account_jobs_for_ready_files": {
        "task": "tenants.tasks.scan_for_ready_files",
        "schedule": 10.0, #run every 10 seconds
    },
}
