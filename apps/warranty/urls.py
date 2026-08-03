from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.warranty import views

app_name = "warranty"

router = DefaultRouter()
router.register(r"warranties", views.WarrantyViewSet, basename="api-warranty")

urlpatterns = [
    path("api/", include(router.urls)),
]
