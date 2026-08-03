from apps.service_desk.reporting.exports import tickets_csv
from apps.service_desk.services.dashboard_service import DashboardService


def ticket_summary_report(company=None, user=None) -> dict:
    return {
        "kpis": DashboardService.summary(company=company, user=user),
        "csv_preview": tickets_csv(
            __import__("apps.service_desk.models", fromlist=["Ticket"]).Ticket.objects.filter(
                **({"company": company} if company else {})
            )[:50]
        )[:2000],
    }
