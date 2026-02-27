import os
from celery import Celery
from celery.schedules import crontab
import tenants.tasks

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palmtree_etl.settings")

app = Celery("palmtree_etl")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "promote_dropzone_files_every_minute": {
        "task": "tenants.tasks.promote_dropzone_files",
        "schedule": 60.0,  # run every minute
    },
}
