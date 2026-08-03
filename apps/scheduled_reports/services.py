from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from apps.scheduled_reports.models import ReportRun, ScheduledReport
from apps.service_desk.reporting.exports import tickets_csv
from apps.service_desk.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)


class ScheduledReportService:
    @staticmethod
    def schedule_next(report: ScheduledReport, from_dt=None):
        base = from_dt or timezone.now()
        if report.frequency == ScheduledReport.Frequency.DAILY:
            nxt = base + timedelta(days=1)
        elif report.frequency == ScheduledReport.Frequency.MONTHLY:
            nxt = base + timedelta(days=30)
        else:
            nxt = base + timedelta(days=7)
        report.next_run_at = nxt
        report.save(update_fields=["next_run_at", "updated_at"])
        return nxt

    @classmethod
    def run(cls, report: ScheduledReport) -> ReportRun:
        run = ReportRun.objects.create(report=report, state=ReportRun.State.SUCCESS)
        try:
            content, ext, row_count = cls._render(report)
            out_dir = Path(settings.MEDIA_ROOT) / "reports" / str(report.company_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{report.pk}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            path = out_dir / filename
            path.write_text(content, encoding="utf-8")
            run.artifact_path = str(path.relative_to(settings.MEDIA_ROOT))
            run.row_count = row_count
            run.finished_at = timezone.now()
            run.save()
            cls._email(report, path, content, ext)
            report.last_run_at = timezone.now()
            report.save(update_fields=["last_run_at", "updated_at"])
            cls.schedule_next(report)
        except Exception as exc:  # noqa: BLE001
            logger.exception("scheduled_report_failed")
            run.state = ReportRun.State.FAILED
            run.error_message = str(exc)
            run.finished_at = timezone.now()
            run.save()
        return run

    @staticmethod
    def _render(report: ScheduledReport) -> tuple[str, str, int]:
        company = report.company
        if report.report_type == ScheduledReport.ReportType.TICKET_CSV:
            from apps.service_desk.models import Ticket

            qs = Ticket.objects.filter(company=company)
            content = tickets_csv(qs)
            return content, "csv", qs.count()
        if report.report_type == ScheduledReport.ReportType.DASHBOARD_JSON:
            data = DashboardService.summary(company=company)
            return json.dumps(data, indent=2, default=str), "json", 1
        if report.report_type == ScheduledReport.ReportType.SLA_SUMMARY:
            data = DashboardService.summary(company=company)
            payload = {
                "breached_tickets": data.get("breached_tickets"),
                "sla_compliance_pct": data.get("sla_compliance_pct"),
                "open_tickets": data.get("open_tickets"),
            }
            return json.dumps(payload, indent=2), "json", 1
        if report.report_type == ScheduledReport.ReportType.VULN_SUMMARY:
            try:
                from apps.vulnerability_management.services import VulnerabilityService

                data = VulnerabilityService.summary(company)
            except Exception:  # noqa: BLE001
                data = {}
            return json.dumps(data, indent=2, default=str), "json", 1
        return "{}", "json", 0

    @staticmethod
    def _email(report: ScheduledReport, path: Path, content: str, ext: str) -> None:
        recipients = [r for r in (report.recipients or []) if r]
        if not recipients:
            return
        email = EmailMessage(
            subject=f"[ESD Report] {report.name}",
            body=f"Attached: {report.get_report_type_display()} generated at {timezone.now()}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        mime = "text/csv" if ext == "csv" else "application/json"
        email.attach(path.name, content, mime)
        email.send(fail_silently=True)

    @classmethod
    def run_due(cls, company=None) -> int:
        now = timezone.now()
        qs = ScheduledReport.objects.filter(is_active=True).filter(
            models_q_next_run(now)
        )
        if company is not None:
            qs = qs.filter(company=company)
        count = 0
        for report in qs:
            cls.run(report)
            count += 1
        return count


def models_q_next_run(now):
    from django.db.models import Q

    return Q(next_run_at__isnull=True) | Q(next_run_at__lte=now)
