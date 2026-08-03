from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.compliance import views

app_name = "compliance"

router = DefaultRouter()
router.register(r"frameworks", views.ControlFrameworkViewSet, basename="api-framework")
router.register(r"controls", views.ControlViewSet, basename="api-control")
router.register(r"evidence", views.ComplianceEvidenceViewSet, basename="api-evidence")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/bootstrap-iso27001/", views.ComplianceBootstrapAPI.as_view(), name="api-bootstrap"),
]
