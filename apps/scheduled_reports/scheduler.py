from apps.scheduled_reports.services import ScheduledReportService
def run_due():
    return ScheduledReportService.run_due()
