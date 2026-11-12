"""Django settings assembled from validated Metis configuration."""

from pathlib import Path

from kombu import Queue

from projects.correction.attempts.status import QUEUES, STAGES
from projects.correction.metis.config import settings as config

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config.secret_key
DEBUG = config.debug
ALLOWED_HOSTS = config.allowed_hosts
CSRF_TRUSTED_ORIGINS = config.csrf_trusted_origins

INSTALLED_APPS = [
    "projects.correction.attempts.apps.AttemptsConfig",
    "projects.correction.pipeline.apps.PipelineConfig",
    "projects.correction.extractor.apps.ExtractorAppConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "projects.correction.metis.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "projects.correction.metis.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": config.postgres_host,
        "PORT": config.postgres_port,
        "NAME": config.postgres_db,
        "USER": config.postgres_user,
        "PASSWORD": config.postgres_password,
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Recife"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / config.media_root
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = config.redis_url
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": config.broker_visibility_timeout_seconds}
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = config.stage_soft_time_limit_seconds
CELERY_TASK_TIME_LIMIT = config.stage_time_limit_seconds
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = [Queue(name) for name in QUEUES]
CELERY_TASK_ROUTES = {spec.task_name: {"queue": spec.queue} for spec in STAGES}
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "reconcile-runs": {
        "task": "pipeline.reconcile_runs",
        "schedule": config.reconcile_interval_seconds,
        "options": {"queue": "default"},
    }
}
