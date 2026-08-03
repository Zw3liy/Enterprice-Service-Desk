"""Ticketing project package."""

try:
    from .celery import app as celery_app
except Exception:  # Celery optional in lightweight dev installs
    celery_app = None

__all__ = ("celery_app",)
