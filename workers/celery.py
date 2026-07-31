"""Worker entry re-export."""

from ticketing.celery import app

__all__ = ["app"]
