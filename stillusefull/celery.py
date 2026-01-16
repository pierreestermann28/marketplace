import os

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    Celery = None

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stillusefull.settings")

if Celery:
    app = Celery("stillusefull")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
else:
    app = None
