from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.billing import views

app_name = "billing"

router = DefaultRouter()
router.register(r"plans", views.PlanViewSet, basename="api-plan")
router.register(r"invoices", views.InvoiceViewSet, basename="api-invoice")

urlpatterns = [
    path("", views.billing_dashboard, name="dashboard"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("cancel/", views.cancel_subscription, name="cancel"),
    path("invoice/", views.generate_invoice, name="generate_invoice"),
    path("api/", include(router.urls)),
    path("api/subscription/", views.SubscriptionAPI.as_view(), name="api-subscription"),
    path("api/usage/", views.UsageAPI.as_view(), name="api-usage"),
]