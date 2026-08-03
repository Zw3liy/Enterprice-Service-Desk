from django.urls import path

from api.analytics.views import AnalyticsDashboardAPI, AnalyticsExportAPI

urlpatterns = [
    path("dashboard/", AnalyticsDashboardAPI.as_view(), name="api-analytics-dashboard"),
    path("export/tickets.csv", AnalyticsExportAPI.as_view(), name="api-analytics-export"),
]
