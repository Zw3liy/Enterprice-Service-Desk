from apps.service_desk.services.dashboard_service import DashboardService


def collect_kpis(company=None, user=None) -> dict:
    return DashboardService.summary(company=company, user=user)
