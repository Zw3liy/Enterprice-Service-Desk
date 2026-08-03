"""Executive KPI aggregation across ITSM domains."""

from __future__ import annotations

from apps.analytics_engine.reports.agent_reports import agent_workload_report
from apps.analytics_engine.reports.sla_reports import sla_report
from apps.forecasting.services import ForecastingService
from apps.service_desk.models import Asset, KnowledgeArticle, Ticket
from apps.service_desk.services.dashboard_service import DashboardService


class ExecutiveDashboardService:
    @classmethod
    def board_pack(cls, company=None, user=None) -> dict:
        core = DashboardService.summary(company=company, user=user)
        tickets = Ticket.objects.all()
        assets = Asset.objects.all()
        articles = KnowledgeArticle.objects.filter(is_published=True)
        if company is not None:
            tickets = tickets.filter(company=company)
            assets = assets.filter(company=company)
            articles = articles.filter(company=company)

        major = tickets.filter(is_major_incident=True, closed_at__isnull=True).count()
        changes = tickets.filter(ticket_type="change", closed_at__isnull=True).count()
        problems = tickets.filter(ticket_type="problem", closed_at__isnull=True).count()

        forecast = {}
        staffing = {}
        try:
            if company is not None:
                forecast = ForecastingService.ticket_volume_forecast(
                    company, history_days=14, horizon_days=7
                )
                staffing = ForecastingService.staffing_suggestion(company)
        except Exception:
            forecast, staffing = {}, {}

        return {
            "kpis": core,
            "sla": sla_report(company=company),
            "agents": agent_workload_report(company=company)[:10],
            "portfolio": {
                "open_major_incidents": major,
                "open_changes": changes,
                "open_problems": problems,
                "assets": assets.count(),
                "knowledge_articles": articles.count(),
            },
            "forecast": forecast.get("forecast", []),
            "staffing": staffing,
        }
