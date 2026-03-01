import paramiko
import os
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()
HOST = "52.56.242.200"
PORT = 22
USERNAME = os.getenv("SFTP_TEST_USERNAME")
PASSWORD = os.getenv("SFTP_TEST_PASSWORD")
REMOTE_DIR = "drop"  # because user home is already the drop root
# ==================

def upload_test_file():
    # Create a local test file
    filename = f"test_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    local_path = os.path.join("/tmp", filename)

    with open(local_path, "w") as f:
        f.write("This is a test file uploaded via SFTP.\n")

    print(f"Created local test file: {local_path}")

    transport = paramiko.Transport((HOST, PORT))
    transport.connect(username=USERNAME, password=PASSWORD)

    sftp = paramiko.SFTPClient.from_transport(transport)

    remote_path = f"{REMOTE_DIR}/{filename}"

    print(f"Uploading to {remote_path} ...")
    sftp.put(local_path, remote_path)

    print("Upload successful ✅")

    sftp.close()
    transport.close()


if __name__ == "__main__":
    upload_test_file()