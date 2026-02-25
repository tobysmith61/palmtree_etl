<p align="center">
    <img src="core/static/core/images/branding/palmtree/palmtree_logo_clean_no_bg.png" alt="palmTree Logo" width="120">
</p>

<h1 align="center">palmTree ETL</h1>

<div align="center">
    A lightweight, multi-tenant ETL management platform by
</div>

<div align="center">
    <img src="core/static/core/images/branding/bitsprout/BitSprout1-transparent.png" alt="BitSprout Logo" width="120">
</div>

START REDIS (on separate terminal)
brew services start redis
redis-cli ping

START CELERY TASKS (on separate terminal)
celery -A palmtree_etl worker -l info

FOLDER WATCHER (on separate terminal)
python manage.py watch_incoming

CREATE SFTP DROP FOLDER
sudo mkdir -p /srv/sftp_drops
sudo chown -R ubuntu:ubuntu /srv/sftp_drops
