# file_ingestion/management/commands/watch_incoming.py
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from django.conf import settings
from django.core.management.base import BaseCommand
from file_ingestion.tasks import process_file

class IncomingHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        print("Detected file:", event.src_path)  # <-- debug
        process_file.delay(event.src_path)
        print(f"[Watcher] Task queued for: {event.src_path}")  # <-- debug

class Command(BaseCommand):
    help = "Watch incoming directory for new files"

    def handle(self, *args, **options):
        observer = Observer()
        observer.schedule(
            IncomingHandler(),
            str(settings.INGESTION_INCOMING_DIR),
            recursive=False,
        )
        observer.start()
        self.stdout.write("Watching incoming directory...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
