from apps.service_desk.services.dashboard_service import DashboardService

def ai_report(company=None):
    return {"kpis": DashboardService.summary(company=company)}
