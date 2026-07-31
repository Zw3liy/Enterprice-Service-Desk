from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.monitoring_engine import views

app_name = "monitoring"

router = DefaultRouter()
router.register(r"alerts", views.MonitoringAlertViewSet, basename="api-monitoring-alert")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/ingest/", views.MonitoringIngestAPI.as_view(), name="api-ingest"),
]