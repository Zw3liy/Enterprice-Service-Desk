"""Monitoring alert ingestion and incident correlation."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.incident_management.services import IncidentService
from apps.monitoring_engine.models import MonitoringAlert
from apps.service_desk.models import Ticket
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class MonitoringService:
    @classmethod
    @transaction.atomic
    def ingest(
        cls,
        company,
        *,
        title: str,
        description: str = "",
        severity: str = MonitoringAlert.Severity.WARNING,
        source: str = "generic",
        external_id: str = "",
        host: str = "",
        service: str = "",
        payload: dict | None = None,
        open_incident: bool = True,
        actor=None,
    ) -> MonitoringAlert:
        alert = None
        if external_id:
            alert = MonitoringAlert.objects.filter(
                company=company, source=source, external_id=external_id, state=MonitoringAlert.State.OPEN
            ).first()
        if alert is None:
            alert = MonitoringAlert.objects.create(
                company=company,
                title=title[:240],
                description=description,
                severity=severity,
                source=source,
                external_id=external_id,
                host=host,
                service=service,
                payload=payload or {},
            )
        else:
            alert.description = description or alert.description
            alert.severity = severity
            alert.payload = payload or alert.payload
            alert.save()

        if open_incident and alert.ticket_id is None and severity in {
            MonitoringAlert.Severity.CRITICAL,
            MonitoringAlert.Severity.WARNING,
        }:
            ticket = IncidentService.create_incident(
                title=f"[{source}] {title}"[:240],
                description=description or f"Alert from {source} on {host or service}",
                company=company,
                channel=Ticket.Channel.MONITORING,
                actor=actor,
                auto_assign=True,
                run_ai=True,
            )
            if severity == MonitoringAlert.Severity.CRITICAL:
                ticket.is_major_incident = True
                ticket.save(update_fields=["is_major_incident", "updated_at"])
            alert.ticket = ticket
            alert.save(update_fields=["ticket", "updated_at"])
            AuditService.log(
                action="monitoring.alert_ticket",
                ticket=ticket,
                company=company,
                actor=actor,
                message=f"Opened from alert {alert.pk}",
                metadata={"source": source, "external_id": external_id},
            )
        logger.info("monitoring_ingest alert=%s severity=%s", alert.pk, severity)
        return alert

    @classmethod
    def resolve(cls, alert: MonitoringAlert, actor=None) -> MonitoringAlert:
        alert.state = MonitoringAlert.State.RESOLVED
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["state", "resolved_at", "updated_at"])
        return alert
