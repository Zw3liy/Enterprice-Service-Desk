from apps.service_desk.services.dashboard_service import DashboardService


def dashboard_summary(**kwargs):
    return DashboardService.summary(**kwargs)
