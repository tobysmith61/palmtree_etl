# myapp/views.py
from django.shortcuts import render
import psutil
import shutil
from celery import Celery
from django.db import connections
from django.db.utils import OperationalError

app = Celery("palmtree_etl")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

def is_process_running(name):
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            pname = proc.info.get("name") or ""
            if name.lower() in pname.lower() or any(name.lower() in str(c).lower() for c in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def is_celery_beat_running():
    for proc in psutil.process_iter(["cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if "celery" in [c.lower() for c in cmdline] and "beat" in [c.lower() for c in cmdline]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def get_db_status():
    db_conn = connections["default"]
    try:
        c = db_conn.cursor()
        c.execute("SELECT 1;")
        return "ok"
    except OperationalError:
        return "down"

def healthcheck_page(request):
    status = {}

    # Services
    status["celery_worker"] = "running" if is_process_running("celery") else "stopped"
    status["celery_beat"] = "running" if is_celery_beat_running() else "stopped"
    status["database"] = get_db_status()

    # Map CSS classes for template
    status["celery_worker_class"] = "ok" if status["celery_worker"]=="running" else "down"
    status["celery_beat_class"] = "ok" if status["celery_beat"]=="running" else "down"
    status["database_class"] = "ok" if status["database"]=="ok" else "down"

    # System resources
    total, used, free = shutil.disk_usage("/")
    status["disk"] = {"total_gb": total//2**30, "used_gb": used//2**30, "free_gb": free//2**30}

    mem = psutil.virtual_memory()
    status["memory"] = {
        "total_mb": mem.total//1024//1024,
        "used_mb": mem.used//1024//1024,
        "free_mb": mem.available//1024//1024
    }

    return render(request, "healthcheck.html", {"status": status})
