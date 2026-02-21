#!/bin/bash
# deploy.sh - first-time or subsequent deploy of PalmTree ETL to EC2

# --- CONFIG ---
EC2_USER="ubuntu"                                                      # EC2 user
EC2_HOST="35.178.99.172"                                               # EC2 public IPv4
PEM_PATH="$HOME/.ssh/palmtree_etl/palmtree-sftp-server-dev-key.pem"    # Full path to PEM
APP_DIR="/var/www/palmtree_etl"                                        # App folder on EC2
SERVICE_NAME="palmtree_etl"                                            # systemd service name

# --- SAFETY ---
set -e  # exit on first error

echo "Deploying PalmTree ETL to $EC2_USER@$EC2_HOST..."

ssh -o StrictHostKeyChecking=accept-new -i "$PEM_PATH" "$EC2_USER@$EC2_HOST" << EOF
  set -e

  # Ensure folder exists
  sudo mkdir -p $APP_DIR
  sudo chown \$USER:\$USER $APP_DIR

  cd $APP_DIR

  # First-time deploy: clone if .git does not exist
  if [ ! -d ".git" ]; then
    echo "Cloning repo for the first time..."
    git clone git@github.com:yourusername/palmtree_etl.git .
  else
    echo "Updating existing repo..."
    git reset --hard origin/main
    git pull origin main
  fi

  sudo systemctl restart $SERVICE_NAME
EOF

echo "✅ Deployment finished."
