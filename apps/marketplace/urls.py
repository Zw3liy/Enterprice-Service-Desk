from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.marketplace import views

app_name = "marketplace"

router = DefaultRouter()
router.register(r"catalog", views.MarketplaceCatalogViewSet, basename="api-mkt-catalog")
router.register(r"installed", views.InstalledAppViewSet, basename="api-mkt-installed")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/install/", views.MarketplaceInstallAPI.as_view(), name="api-install"),
]
