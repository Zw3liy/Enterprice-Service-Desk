from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.event_engine import views

app_name = "event_engine"

router = DefaultRouter()
router.register(r"events", views.DomainEventViewSet, basename="api-domain-event")

urlpatterns = [
    path("api/", include(router.urls)),
]
