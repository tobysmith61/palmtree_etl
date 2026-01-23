<p align="center">
  <img src="static/core/images/palmtree_logo_clean_no_bg.png" alt="Palmtree Logo" width="120">
</p>

<h1 align="center">Palmtree ETL</h1>

<p align="center">
A lightweight, multi-tenant ETL management platform by BitSprout
</p>

START REDIS (on separate terminal)
brew services start redis
redis-cli ping

START CELERY TASKS (on separate terminal)
celery -A palmtree_etl worker -l info

FOLDER WATCHER (on separate terminal)
python manage.py watch_incoming
