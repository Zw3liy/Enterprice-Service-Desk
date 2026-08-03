from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.soc_center import views

app_name = "soc"

router = DefaultRouter()
router.register(r"incidents", views.SecurityIncidentViewSet, basename="api-soc-incident")
router.register(r"playbooks", views.SOCPlaybookViewSet, basename="api-soc-playbook")
router.register(r"runs", views.PlaybookRunViewSet, basename="api-soc-run")

urlpatterns = [
    path("api/", include(router.urls)),
]
