from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.scheduled_reports import views

app_name = "scheduled_reports"

router = DefaultRouter()
router.register(r"reports", views.ScheduledReportViewSet, basename="api-scheduled-report")
router.register(r"runs", views.ReportRunViewSet, basename="api-report-run")

urlpatterns = [
    path("api/", include(router.urls)),
]
