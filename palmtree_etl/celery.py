import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palmtree_etl.settings")

app = Celery("palmtree_etl")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
