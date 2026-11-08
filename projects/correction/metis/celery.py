"""App Celery do Metis; a configuração vem do Django (prefixo CELERY_)."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projects.correction.metis.settings")

app = Celery("metis")
app.config_from_object("django.conf:settings", namespace="CELERY")
