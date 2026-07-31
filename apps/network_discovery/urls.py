from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.network_discovery import views

app_name = "discovery"

router = DefaultRouter()
router.register(r"scans", views.DiscoveryScanViewSet, basename="api-discovery-scan")

urlpatterns = [
    path("api/", include(router.urls)),
]
