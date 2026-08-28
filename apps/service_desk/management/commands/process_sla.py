"""
Scheduled SLA processing.

Run on a timer (cron, systemd timer, Task Scheduler, or any external
scheduler — the repository deliberately declares no broker/worker
dependency):

    python manage.py process_sla

Every run is idempotent: escalations are unique per (ticket SLA, kind),
so running it every minute produces at most one warning and one breach
record per clock.

Every non-dry-run execution writes one ``SLARunLog`` row (start time,
finish time, records processed, warnings/breaches raised, success or
failure with the exception message) — this is the "last run,
processed records, warnings, breaches, failures and duration"
monitoring the mission requires, queryable after the process has
exited and its stdout is gone. See docs/operations/SLA_SCHEDULING.md
for Windows Task Scheduler and container scheduling setup — this file
intentionally starts no thread, timer or loop of its own; it runs
once and exits, exactly once per external trigger.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.service_desk.models import SLAEscalation, SLARunLog, TicketSLA
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

        return self._run_with_monitoring(now)

    def _run_with_monitoring(self, now):

        queryset = self._active_queryset()
        processed_count = queryset.count()

        run_log = SLARunLog.objects.create(
            started_at=now,
            processed_count=processed_count,
        )

        try:
            created = SLAService.process_due(now=now)
        except Exception as exc:
            run_log.finished_at = timezone.now()
            run_log.succeeded = False
            run_log.error_message = str(exc)[:4000]
            run_log.save(
                update_fields=["finished_at", "succeeded", "error_message"]
            )
            raise

        breaches = [e for e in created if e.is_breach]
        warnings = [e for e in created if not e.is_breach]

        run_log.finished_at = timezone.now()
        run_log.warnings_count = len(warnings)
        run_log.breaches_count = len(breaches)
        run_log.succeeded = True
        run_log.save(
            update_fields=[
                "finished_at",
                "warnings_count",
                "breaches_count",
                "succeeded",
            ]
        )

        for escalation in created:
            self.stdout.write(
                f"{escalation.get_kind_display()}: "
                f"ticket #{escalation.ticket_sla.ticket_id} — "
                f"{escalation.detail}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA processing complete: {processed_count} clock(s) "
                f"evaluated, {len(warnings)} warning(s), "
                f"{len(breaches)} breach(es) raised in "
                f"{run_log.duration_seconds:.2f}s."
            )
        )

    @staticmethod
    def _active_queryset():
        return (
            TicketSLA.objects.filter(paused=False)
            .exclude(
                first_responded_at__isnull=False,
                resolved_at__isnull=False,
            )
        )

    def _dry_run(self, now):

        pending = 0

        records = self._active_queryset().select_related("ticket", "policy")

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
