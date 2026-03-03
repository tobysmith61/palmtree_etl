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

after adding new tables and deploying:
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO palmtree_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO palmtree_app;

get latest fixtures
python manage.py import_fixtures --dir=fixtures

because gunicorn runs as ubuntu and ftps drop folders need correc perms do this:
sudo chown -R ubuntu:ubuntu /srv/sftp_drops



NB sftpdropzone rows are created on dev/staging and deployed, then sftp account on remote admin

sFTP folders:
=============
✅ Set ownership
sudo chown root:root /srv/sftp_drops
sudo chown root:root /srv/sftp_drops/stellant
sudo chown root:root /srv/sftp_drops/stellant/dms002
sudo chown stellant_dms002:stellant_dms002 /srv/sftp_drops/stellant/dms002/drop

✅ Set permissions
sudo chmod 755 /srv/sftp_drops
sudo chmod 755 /srv/sftp_drops/stellant
sudo chmod 755 /srv/sftp_drops/stellant/dms002
sudo chmod 755 /srv/sftp_drops/stellant/dms002/drop

🔎 Verify everything in one go
ls -ld /srv/sftp_drops \
       /srv/sftp_drops/stellant \
       /srv/sftp_drops/stellant/dms002 \
       /srv/sftp_drops/stellant/dms002/drop

You should see:
drwxr-xr-x root root
drwxr-xr-x root root
drwxr-xr-x root root
drwxr-xr-x stellant_dms002 stellant_dms002
