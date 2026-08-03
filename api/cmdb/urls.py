from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.cmdb.views import CIClassViewSet, ConfigurationItemViewSet, DiscoveryIngestAPI

router = DefaultRouter()
router.register(r"cis", ConfigurationItemViewSet, basename="gw-ci")
router.register(r"classes", CIClassViewSet, basename="gw-ci-class")

urlpatterns = [
    path("discovery/", DiscoveryIngestAPI.as_view(), name="gw-discovery"),
]
urlpatterns += router.urls
