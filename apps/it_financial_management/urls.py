from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.it_financial_management import views

app_name = "finance"

router = DefaultRouter()
router.register(r"cost-centers", views.CostCenterViewSet, basename="api-cost-center")
router.register(r"budgets", views.BudgetViewSet, basename="api-budget")
router.register(r"chargebacks", views.ChargebackViewSet, basename="api-chargeback")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/bootstrap/", views.FinanceBootstrapAPI.as_view(), name="api-bootstrap"),
]
