#!/bin/bash

# Usage: ./create_dropzone.sh <account_name> <system_name>

ACCOUNT="$1"
SYSTEM="$2"
SFTP_USER="${ACCOUNT}_${SYSTEM}"
SFTP_GROUP="${SFTP_USER}"
BASE_PATH="/srv/sftp_drops"
ACCOUNT_PATH="$BASE_PATH/$ACCOUNT"
SYSTEM_PATH="$ACCOUNT_PATH/$SYSTEM"
DROP_PATH="$SYSTEM_PATH/drop"
READY_PATH="$SYSTEM_PATH/ready"
PROCESSED_PATH="$SYSTEM_PATH/processed"
FAILED_PATH="$SYSTEM_PATH/failed"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to pause
pause() {
    read -p "Press ENTER to continue or CTRL+C to cancel"
}

# 1. Check parameters
if [ -z "$ACCOUNT" ] || [ -z "$SYSTEM" ]; then
    echo -e "${RED}Usage: $0 <account_name> <system_name>${NC}"
    exit 1
fi

# 2. Warn if not root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Warning: You are not root. The script will use sudo for privileged commands.${NC}"
fi

# 3. Show summary
echo -e "${GREEN}Creating SFTP dropzone for account: $ACCOUNT, system: $SYSTEM${NC}"
echo "Base path: $BASE_PATH"
echo "SFTP user/group: $SFTP_USER"
pause

# 4. Ensure account directory exists
if [ ! -d "$ACCOUNT_PATH" ]; then
    echo -e "${YELLOW}Account directory does not exist. Creating: $ACCOUNT_PATH${NC}"
    pause
    sudo mkdir -p "$ACCOUNT_PATH"
    sudo chown root:root "$ACCOUNT_PATH"
    sudo chmod 755 "$ACCOUNT_PATH"
else
    echo -e "${GREEN}Account directory exists: $ACCOUNT_PATH${NC}"
fi

# 5. Create group
if ! getent group "$SFTP_GROUP" > /dev/null; then
    echo -e "${YELLOW}Creating group: $SFTP_GROUP${NC}"
    pause
    sudo groupadd "$SFTP_GROUP"
else
    echo -e "${GREEN}Group already exists: $SFTP_GROUP${NC}"
fi

# 6. Create user
if ! id "$SFTP_USER" > /dev/null 2>&1; then
    echo -e "${YELLOW}Creating SFTP user: $SFTP_USER${NC}"
    pause
    sudo useradd -g "$SFTP_GROUP" -s /usr/sbin/nologin "$SFTP_USER"

    # 6a. Generate random 16-character password
    SFTP_PWD=$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9' | head -c16)
    echo -e "${YELLOW}Setting random password for $SFTP_USER${NC}"
    pause
    echo "$SFTP_USER:$SFTP_PWD" | sudo chpasswd
    echo -e "${GREEN}SFTP user password generated:${NC} $SFTP_PWD"
else
    echo -e "${GREEN}User already exists: $SFTP_USER${NC}"
fi

# 7. Create system folder
if [ ! -d "$SYSTEM_PATH" ]; then
    echo -e "${YELLOW}Creating system folder: $SYSTEM_PATH${NC}"
    pause
    sudo mkdir -p "$SYSTEM_PATH"
    sudo chown root:root "$SYSTEM_PATH"
    sudo chmod 755 "$SYSTEM_PATH"
else
    echo -e "${GREEN}System folder exists: $SYSTEM_PATH${NC}"
fi

# 8. Create drop folder
if [ ! -d "$DROP_PATH" ]; then
    echo -e "${YELLOW}Creating drop folder: $DROP_PATH${NC}"
    pause
    sudo mkdir -p "$DROP_PATH"
else
    echo -e "${GREEN}Drop folder exists: $DROP_PATH${NC}"
fi

# 9. Create ready folder
if [ ! -d "$READY_PATH" ]; then
    echo -e "${YELLOW}Creating ready folder: $READY_PATH${NC}"
    pause
    sudo mkdir -p "$READY_PATH"
else
    echo -e "${GREEN}Ready folder exists: $READY_PATH${NC}"
fi

# Create processed folder
if [ ! -d "$PROCESSED_PATH" ]; then
    echo -e "${YELLOW}Creating processed folder: $PROCESSED_PATH${NC}"
    pause
    sudo mkdir -p "$PROCESSED_PATH"
else
    echo -e "${GREEN}Processed folder exists: $PROCESSED_PATH${NC}"
fi

# Create processed folder
if [ ! -d "$PROCESSED_PATH" ]; then
    echo -e "${YELLOW}Creating processed folder: $PROCESSED_PATH${NC}"
    pause
    sudo mkdir -p "$PROCESSED_PATH"
else
    echo -e "${GREEN}Processed folder exists: $PROCESSED_PATH${NC}"
fi

# 10. Set ownership
echo -e "${YELLOW}Setting ownership...${NC}"
pause
sudo chown $SFTP_USER:$SFTP_GROUP "$DROP_PATH"
sudo chown ubuntu:www-data "$READY_PATH"
sudo chown ubuntu:www-data "$PROCESSED_PATH"
sudo chown ubuntu:www-data "$FAILED_PATH"
sudo chown root:root "$SYSTEM_PATH"

# 11. Set permissions
echo -e "${YELLOW}Setting permissions...${NC}"
pause
sudo chmod 2775 "$DROP_PATH"
sudo chmod 775 "$READY_PATH"
sudo chmod 775 "$PROCESSED_PATH"
sudo chmod 775 "$FAILED_PATH"
sudo chmod 755 "$SYSTEM_PATH"

# 12. Add ubuntu to SFTP group if not already
if id -nG ubuntu | grep -qw "$SFTP_GROUP"; then
    echo -e "${GREEN}User ubuntu already in group $SFTP_GROUP${NC}"
else
    echo -e "${YELLOW}Adding ubuntu to group $SFTP_GROUP${NC}"
    pause
    sudo usermod -aG "$SFTP_GROUP" ubuntu
fi

# 13. Configure SSH for chrooted SFTP
SFTP_SSH_CONFIG="\nMatch User $SFTP_USER\n    ChrootDirectory $SYSTEM_PATH\n    ForceCommand internal-sftp\n    PasswordAuthentication yes\n    AllowTcpForwar
ding no\n    X11Forwarding no"

if ! grep -q "Match User $SFTP_USER" /etc/ssh/sshd_config; then
    echo -e "${YELLOW}Adding SSH config for $SFTP_USER to /etc/ssh/sshd_config${NC}"
    pause
    echo -e "$SFTP_SSH_CONFIG" | sudo tee -a /etc/ssh/sshd_config > /dev/null
else
    echo -e "${GREEN}SSH config for $SFTP_USER already exists${NC}"
fi

# 14. Restart SSH service
echo -e "${YELLOW}Restarting SSH service to apply changes...${NC}"
pause
sudo systemctl restart ssh

# 15. Final verification
echo -e "${GREEN}Final folder listing:${NC}"
ls -l "$SYSTEM_PATH"

echo -e "${GREEN}Group membership of $SFTP_GROUP:${NC}"
getent group "$SFTP_GROUP"

echo -e "${GREEN}SFTP user password:${NC} $SFTP_PWD"
echo -e "${GREEN}Script completed.${NC}"
