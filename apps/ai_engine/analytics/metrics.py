from apps.service_desk.services.dashboard_service import DashboardService

def ai_metrics(company=None):
    return DashboardService.summary(company=company)
