START REDIS (on separate terminal)
brew services start redis
redis-cli ping

START CELERY TASKS (on separate terminal)
celery -A palmtree_etl worker -l info

FOLDER WATCHER (on separate terminal)
python manage.py watch_incoming
