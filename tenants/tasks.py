from pathlib import Path
import shutil

DROP_FOLDER = Path("/srv/sftp_drops/voltaris/777/drop")
READY_FOLDER = Path("/srv/sftp_drops/voltaris/777/ready")  # <- correct

def promote_dropzone_files():
    READY_FOLDER.mkdir(exist_ok=True)  # ensure folder exists
    for file_path in DROP_FOLDER.iterdir():
        if file_path.is_file():
            shutil.move(str(file_path), READY_FOLDER / file_path.name)
            print(f"Moved {file_path.name} to ready")
            