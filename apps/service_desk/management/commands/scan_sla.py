"""Management command to evaluate SLA breaches and escalations."""

from django.core.management.base import BaseCommand

from apps.service_desk.services.sla_service import SLAService


class Command(BaseCommand):
    help = "Scan open tickets for SLA breaches and trigger escalations."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, default=None)

    def handle(self, *args, **options):
        count = SLAService.scan_open_tickets(company_id=options["company_id"])
        self.stdout.write(self.style.SUCCESS(f"Processed breaches/escalations: {count}"))
