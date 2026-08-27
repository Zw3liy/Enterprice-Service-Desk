"""
Scheduled SLA processing.

Run on a timer (cron, systemd timer, Task Scheduler, or any external
scheduler — the repository deliberately declares no broker/worker
dependency):

    python manage.py process_sla

Every run is idempotent: escalations are unique per (ticket SLA, kind),
so running it every minute produces at most one warning and one breach
record per clock.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.service_desk.models import SLAEscalation, TicketSLA
from apps.service_desk.services.sla_service import SLAService


class Command(BaseCommand):

    help = "Evaluate live SLA clocks and raise warnings/breaches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Report what would be escalated without writing "
                "escalation records."
            ),
        )

    def handle(self, *args, **options):

        now = timezone.now()

        if options["dry_run"]:
            return self._dry_run(now)

        created = SLAService.process_due(now=now)

        breaches = [e for e in created if e.is_breach]
        warnings = [e for e in created if not e.is_breach]

        for escalation in created:
            self.stdout.write(
                f"{escalation.get_kind_display()}: "
                f"ticket #{escalation.ticket_sla.ticket_id} — "
                f"{escalation.detail}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA processing complete: {len(warnings)} warning(s), "
                f"{len(breaches)} breach(es) raised."
            )
        )

    def _dry_run(self, now):

        pending = 0

        records = (
            TicketSLA.objects.filter(paused=False)
            .select_related("ticket", "policy")
            .exclude(
                first_responded_at__isnull=False,
                resolved_at__isnull=False,
            )
        )

        for record in records:
            state = record.overall_state(now)

            if state in (TicketSLA.STATE_AT_RISK, TicketSLA.STATE_BREACHED):
                pending += 1
                self.stdout.write(
                    f"[{state}] ticket #{record.ticket_id} "
                    f"response due {record.response_due_at:%Y-%m-%d %H:%M}, "
                    f"resolution due {record.resolution_due_at:%Y-%m-%d %H:%M}"
                )

        already = SLAEscalation.objects.count()

        self.stdout.write(
            self.style.WARNING(
                f"Dry run: {pending} clock(s) at risk or breached; "
                f"{already} escalation(s) already recorded. "
                "Nothing was written."
            )
        )
