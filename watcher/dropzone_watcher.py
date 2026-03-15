import time
import shutil
import logging
from pathlib import Path
from threading import Thread, Lock

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# === CONFIG ===
BASE_FOLDER = Path("/srv/sftp_drops")
READY_FOLDER_NAME = "ready"

STABLE_SECONDS = 60
CHECK_INTERVAL = 5
# ==============

processing_files = set()
processing_lock = Lock()


class DropzoneHandler(FileSystemEventHandler):
    """
    Watches for completed uploads in any 'drop' folder.
    Moves files to corresponding 'ready' folder once stable.
    """

    def on_created(self, event):
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def _handle(self, file_path: Path):
        """
        Start tracking a file if it's inside a 'drop' folder.
        """

        # Ensure it's inside a drop directory
        if file_path.parent.name != "drop":
            return

        with processing_lock:
            if file_path in processing_files:
                return
            processing_files.add(file_path)

        logger.info(f"Tracking file: {file_path}")

        Thread(
            target=self._wait_and_promote,
            args=(file_path,),
            daemon=True
        ).start()

    def _wait_and_promote(self, file_path: Path):
        """
        Wait until file size is stable for STABLE_SECONDS,
        then move it to the ready folder.
        """

        try:
            last_size = -1
            stable_start = None

            while True:

                if not file_path.exists():
                    logger.info(f"File disappeared: {file_path}")
                    return

                current_size = file_path.stat().st_size

                if current_size == last_size:
                    if stable_start is None:
                        stable_start = time.time()
                    elif time.time() - stable_start >= STABLE_SECONDS:
                        self._promote(file_path)
                        return
                else:
                    stable_start = None
                    last_size = current_size

                time.sleep(CHECK_INTERVAL)

        finally:
            with processing_lock:
                processing_files.discard(file_path)

    def _promote(self, file_path: Path):
        """
        Copy file to ready folder and delete original.
        """

        ready_folder = file_path.parent.parent / READY_FOLDER_NAME
        ready_folder.mkdir(exist_ok=True)

        destination = ready_folder / file_path.name

        try:
            shutil.copy2(file_path, destination)
            logger.info(f"Copied: {file_path} → {destination}")

            file_path.unlink()
            logger.info(f"Deleted original: {file_path}")

        except Exception:
            logger.exception(f"Failed to promote file: {file_path}")


def start_dropzone_watcher():
    """
    Starts the filesystem observer.
    """

    if not BASE_FOLDER.exists():
        logger.error(f"Base folder does not exist: {BASE_FOLDER}")
        return

    event_handler = DropzoneHandler()
    observer = Observer()

    observer.schedule(event_handler, str(BASE_FOLDER), recursive=True)
    observer.start()

    logger.info(f"Watching: {BASE_FOLDER}")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_dropzone_watcher()