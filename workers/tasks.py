"""Celery / background tasks for the Enterprise Service Desk."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def scan_sla_task(company_id=None):
    from apps.service_desk.services.sla_service import SLAService

    count = SLAService.scan_open_tickets(company_id=company_id)
    logger.info("task.scan_sla count=%s", count)
    return count


def deliver_webhooks_task(company_id: int, event: str, payload: dict):
    from apps.service_desk.models import Company
    from apps.webhooks.services import WebhookService

    company = Company.objects.filter(pk=company_id).first()
    if not company:
        return 0
    deliveries = WebhookService.dispatch(company, event, payload)
    return len(deliveries)


def snapshot_usage_task(company_id: int | None = None):
    from apps.billing.usage import snapshot_usage
    from apps.service_desk.models import Company

    qs = Company.objects.filter(is_active=True)
    if company_id:
        qs = qs.filter(pk=company_id)
    results = {}
    for company in qs:
        results[company.slug] = snapshot_usage(company)
    return results


def enrich_ticket_task(ticket_id: int):
    from apps.service_desk.models import Ticket
    from apps.service_desk.services.ai_service import AIService

    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        return False
    AIService.enrich_ticket(ticket)
    return True


def run_due_reports_task(company_id=None):
    from apps.scheduled_reports.services import ScheduledReportService
    from apps.service_desk.models import Company

    company = Company.objects.filter(pk=company_id).first() if company_id else None
    return ScheduledReportService.run_due(company=company)


def debug_task():
    return {"ok": True}


# Celery-bound variants when Celery app is available
try:
    from ticketing.celery import app as celery_app

    if celery_app is not None:

        @celery_app.task(name="esd.scan_sla")
        def celery_scan_sla(company_id=None):
            return scan_sla_task(company_id)

        @celery_app.task(name="esd.deliver_webhooks")
        def celery_deliver_webhooks(company_id: int, event: str, payload: dict):
            return deliver_webhooks_task(company_id, event, payload)

        @celery_app.task(name="esd.snapshot_usage")
        def celery_snapshot_usage(company_id=None):
            return snapshot_usage_task(company_id)

        @celery_app.task(name="esd.enrich_ticket")
        def celery_enrich_ticket(ticket_id: int):
            return enrich_ticket_task(ticket_id)

except Exception:  # pragma: no cover
    pass
