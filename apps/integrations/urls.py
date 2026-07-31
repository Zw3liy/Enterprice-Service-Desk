from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.integrations import views

app_name = "integrations"

router = DefaultRouter()
router.register(
    r"connections", views.IntegrationConnectionViewSet, basename="api-integration"
)

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/providers/", views.IntegrationProvidersAPI.as_view(), name="api-providers"),
]
