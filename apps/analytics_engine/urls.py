from django.urls import path

from apps.analytics_engine import views

app_name = "analytics_engine"

urlpatterns = [
    path("api/kpis/", views.AnalyticsKPIAPI.as_view(), name="api-kpis"),
    path("api/snapshots/", views.AnalyticsSnapshotAPI.as_view(), name="api-snapshots"),
    path("api/sla/", views.AnalyticsSLAAPI.as_view(), name="api-sla"),
    path("api/agents/", views.AnalyticsAgentsAPI.as_view(), name="api-agents"),
    path("api/export/tickets.csv", views.AnalyticsExportCSVAPI.as_view(), name="api-export-csv"),
    path("api/export/kpis.pdf", views.AnalyticsExportPDFAPI.as_view(), name="api-export-pdf"),
]
