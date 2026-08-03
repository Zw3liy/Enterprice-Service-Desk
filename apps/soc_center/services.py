from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.incident_management.services import IncidentService
from apps.service_desk.models import Ticket
from apps.service_desk.services.audit_service import AuditService
from apps.soc_center.models import PlaybookRun, SecurityIncident, SOCPlaybook

logger = logging.getLogger(__name__)


class SOCService:
    @classmethod
    @transaction.atomic
    def open_incident(
        cls,
        company,
        *,
        title: str,
        summary: str = "",
        severity: str = SecurityIncident.Severity.MEDIUM,
        category: str = "general",
        source: str = "manual",
        iocs: list | None = None,
        mitre_tactics: list | None = None,
        assignee=None,
        create_ticket: bool = True,
        actor=None,
    ) -> SecurityIncident:
        ticket = None
        if create_ticket:
            ticket = IncidentService.create_incident(
                title=f"[SOC] {title}"[:240],
                description=summary,
                company=company,
                channel=Ticket.Channel.MONITORING,
                actor=actor,
                auto_assign=True,
                run_ai=True,
            )
            if severity == SecurityIncident.Severity.CRITICAL:
                ticket.is_major_incident = True
                ticket.save(update_fields=["is_major_incident", "updated_at"])
        si = SecurityIncident.objects.create(
            company=company,
            ticket=ticket,
            title=title,
            summary=summary,
            severity=severity,
            category=category,
            source=source,
            assignee=assignee,
            iocs=iocs or [],
            mitre_tactics=mitre_tactics or [],
        )
        AuditService.log(
            action="soc.incident_opened",
            ticket=ticket,
            company=company,
            actor=actor,
            message=title,
            object_type="security_incident",
            object_id=str(si.pk),
        )
        return si

    @classmethod
    def transition(cls, incident: SecurityIncident, state: str, actor=None) -> SecurityIncident:
        incident.state = state
        if state == SecurityIncident.State.CONTAINMENT and not incident.contained_at:
            incident.contained_at = timezone.now()
        if state == SecurityIncident.State.CLOSED:
            incident.closed_at = timezone.now()
        incident.save()
        AuditService.log(
            action="soc.incident_transition",
            ticket=incident.ticket,
            company=incident.company,
            actor=actor,
            message=f"{incident.title} → {state}",
            object_type="security_incident",
            object_id=str(incident.pk),
        )
        return incident

    @classmethod
    def ensure_default_playbooks(cls, company) -> None:
        defaults = [
            (
                "phishing-response",
                "Phishing response",
                [
                    "Quarantine email",
                    "Reset user credentials",
                    "Block sender domain",
                    "Hunt related messages",
                    "User awareness follow-up",
                ],
            ),
            (
                "malware-containment",
                "Malware containment",
                [
                    "Isolate host",
                    "Collect forensic image",
                    "Block IOCs",
                    "Scan peer hosts",
                    "Restore from clean backup",
                ],
            ),
        ]
        for code, name, steps in defaults:
            SOCPlaybook.objects.get_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "description": name,
                    "steps": [{"title": s, "done": False} for s in steps],
                    "is_active": True,
                },
            )

    @classmethod
    @transaction.atomic
    def start_playbook(
        cls, incident: SecurityIncident, playbook: SOCPlaybook, user=None
    ) -> PlaybookRun:
        run = PlaybookRun.objects.create(
            security_incident=incident,
            playbook=playbook,
            started_by=user,
            log=[{"event": "started", "at": timezone.now().isoformat()}],
        )
        if incident.state == SecurityIncident.State.NEW:
            cls.transition(incident, SecurityIncident.State.TRIAGE, actor=user)
        return run

    @classmethod
    def advance_playbook(cls, run: PlaybookRun, note: str = "", user=None) -> PlaybookRun:
        steps = list(run.playbook.steps or [])
        if run.current_step < len(steps):
            step = steps[run.current_step]
            if isinstance(step, dict):
                step = {**step, "done": True, "note": note}
                steps[run.current_step] = step
            run.current_step += 1
            log = list(run.log or [])
            log.append(
                {
                    "event": "step_completed",
                    "step": run.current_step,
                    "note": note,
                    "at": timezone.now().isoformat(),
                    "by": getattr(user, "username", None),
                }
            )
            run.log = log
            if run.current_step >= len(steps):
                run.state = PlaybookRun.State.COMPLETED
                run.finished_at = timezone.now()
            run.save()
            # persist step done flags on playbook template? keep run-local only
        return run
