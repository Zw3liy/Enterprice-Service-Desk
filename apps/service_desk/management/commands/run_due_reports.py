from django.core.management.base import BaseCommand

from apps.scheduled_reports.services import ScheduledReportService


class Command(BaseCommand):
    help = "Execute due scheduled reports."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, default=None)

    def handle(self, *args, **options):
        company_id = options["company_id"]
        company = None
        if company_id:
            from apps.service_desk.models import Company

            company = Company.objects.filter(pk=company_id).first()
        count = ScheduledReportService.run_due(company=company)
        self.stdout.write(self.style.SUCCESS(f"Ran {count} report(s)"))
