"""Metis application package."""

from projects.correction.metis.celery import app as celery_app

__all__ = ("celery_app",)
