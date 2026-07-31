from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.webhooks import views

app_name = "webhooks"

router = DefaultRouter()
router.register(r"endpoints", views.WebhookEndpointViewSet, basename="api-webhook-endpoint")
router.register(r"deliveries", views.WebhookDeliveryViewSet, basename="api-webhook-delivery")

urlpatterns = [
    path("api/", include(router.urls)),
]