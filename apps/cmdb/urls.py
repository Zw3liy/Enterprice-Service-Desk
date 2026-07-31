from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.cmdb import views

app_name = "cmdb_app"

router = DefaultRouter()
router.register(r"cis", views.ConfigurationItemViewSet, basename="api-ci")
router.register(r"classes", views.CIClassViewSet, basename="api-ci-class")

urlpatterns = [
    path("", views.ci_list, name="list"),
    path("new/", views.ci_create, name="create"),
    path("<int:pk>/", views.ci_detail, name="detail"),
    path("api/", include(router.urls)),
    path("api/discovery/", views.DiscoveryIngestAPI.as_view(), name="api-discovery"),
]