from apps.service_desk.services.dashboard_service import DashboardService


def sla_report(company=None) -> dict:
    summary = DashboardService.summary(company=company)
    return {
        "breached_tickets": summary.get("breached_tickets"),
        "sla_compliance_pct": summary.get("sla_compliance_pct"),
        "open_tickets": summary.get("open_tickets"),
    }
