#!/bin/bash
# Usage: sudo ./create_sftp_user.sh <username> <PALMTREEACCOUNT> <SOURCESYSTEMLABEL>
# Example: sudo ./create_sftp_user.sh stellant_sftp_user_dev STELLANT DMS001

set -e

# -----------------------------
# 0️⃣ ROOT CHECK
# -----------------------------
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# -----------------------------
# 1️⃣ INPUTS
# -----------------------------
PALMTREEACCOUNT="$1"
SOURCESYSTEMLABEL="$2"
USERNAME="$3"
ETL_USER="ubuntu"                 # ETL user owning processing/quarantine/archive folders
PASSWORD=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)  # Random ~32 char password

if [[ -z "$USERNAME" || -z "$PALMTREEACCOUNT" || -z "$SOURCESYSTEMLABEL" ]]; then
    echo "Usage: $0 <username> <PALMTREEACCOUNT> <SOURCESYSTEMLABEL>"
    exit 1
fi

# -----------------------------
# 2️⃣ PRE-FLIGHT CHECKS
# -----------------------------
BASE_SITE_DIR="/sftp/$PALMTREEACCOUNT/$SOURCESYSTEMLABEL"
BASE_DIR="$BASE_SITE_DIR/$USERNAME"

# Check if site folder exists
if [[ -d "$BASE_SITE_DIR" ]]; then
    echo "ERROR: Base site directory $BASE_SITE_DIR already exists. Choose a different SOURCESYSTEMLABEL."
    exit 1
fi

# Check if full user folder exists
if [[ -d "$BASE_DIR" ]]; then
    echo "ERROR: Base directory $BASE_DIR already exists. Pick a different username."
    exit 1
fi

# Check if SFTP username exists
if id "$USERNAME" &>/dev/null; then
    echo "ERROR: User $USERNAME already exists. Pick a unique SFTP username."
    exit 1
fi

echo "✅ All pre-checks passed. Proceeding..."

# -----------------------------
# 3️⃣ CREATE USER
# -----------------------------
useradd -m -d "$BASE_DIR" -s /usr/sbin/nologin "$USERNAME"
echo "$USERNAME:$PASSWORD" | chpasswd
echo "SFTP user $USERNAME created with password: $PASSWORD"

# -----------------------------
# 4️⃣ CREATE FOLDER STRUCTURE
# -----------------------------
for folder in drop processing quarantine archive; do
    mkdir -p "$BASE_DIR/$folder"
done

# -----------------------------
# 5️⃣ SET PERMISSIONS
# -----------------------------
# Base site directory owned by ETL user
mkdir -p "$BASE_SITE_DIR"  # just in case
chown "$ETL_USER":"$ETL_USER" "$BASE_SITE_DIR"
chmod 700 "$BASE_SITE_DIR"

# Customer can write to drop
chown "$USERNAME":"$USERNAME" "$BASE_DIR/drop"
chmod 700 "$BASE_DIR/drop"

# ETL owns processing, quarantine, archive
for folder in processing quarantine archive; do
    chown "$ETL_USER":"$ETL_USER" "$BASE_DIR/$folder"
    chmod 700 "$BASE_DIR/$folder"
done

# Lock down base user directory itself
chown "$ETL_USER":"$ETL_USER" "$BASE_DIR"
chmod 700 "$BASE_DIR"

# -----------------------------
# 6️⃣ OUTPUT
# -----------------------------
echo "=============================="
echo "SFTP user setup complete!"
echo "Username: $USERNAME"
echo "Password: $PASSWORD"
echo "Base directory: $BASE_DIR"
echo "Folders:"
echo "  drop          (customer upload)"
echo "  processing    (ETL in progress)"
echo "  quarantine    (ETL admin only)"
echo "  archive       (ETL admin only)"
echo "=============================="
