"""Celery application for background jobs."""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ticketing.settings")

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    app = None
else:
    app = Celery("ticketing")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()

    @app.task(name="service_desk.scan_sla")
    def scan_sla_task(company_id=None):
        from workers.tasks import scan_sla_task as _scan

        return _scan(company_id)

    @app.task(name="service_desk.snapshot_usage")
    def snapshot_usage_task(company_id=None):
        from workers.tasks import snapshot_usage_task as _snap

        return _snap(company_id)

    @app.task(bind=True, name="service_desk.debug_task")
    def debug_task(self):
        return {"request_id": getattr(self.request, "id", None)}
