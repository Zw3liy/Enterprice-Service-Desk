from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.scheduled_reports.models import ReportRun, ScheduledReport
from apps.scheduled_reports.services import ScheduledReportService
from apps.service_desk.models import Company

User = get_user_model()


class ScheduledReportTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="RptCo", slug="rpt-co")
        self.user = User.objects.create_user(
            username="rptadmin", password="pass12345", is_staff=True, email="a@example.com"
        )

    def test_run_dashboard_json(self):
        report = ScheduledReport.objects.create(
            company=self.company,
            name="Weekly KPIs",
            report_type=ScheduledReport.ReportType.DASHBOARD_JSON,
            frequency=ScheduledReport.Frequency.WEEKLY,
            recipients=[self.user.email],
            created_by=self.user,
        )
        run = ScheduledReportService.run(report)
        self.assertEqual(run.state, ReportRun.State.SUCCESS)
        self.assertTrue(run.artifact_path)
        report.refresh_from_db()
        self.assertIsNotNone(report.last_run_at)
        self.assertIsNotNone(report.next_run_at)
