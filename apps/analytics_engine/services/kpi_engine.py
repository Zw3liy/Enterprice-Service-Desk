from apps.service_desk.services.dashboard_service import DashboardService


class KPIEngine:
    @staticmethod
    def compute(company=None, user=None) -> dict:
        return DashboardService.summary(company=company, user=user)
