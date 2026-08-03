from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.it_financial_management.models import Budget, ChargebackEntry, CostCenter
from apps.it_financial_management.serializers import (
    BudgetSerializer,
    ChargebackEntrySerializer,
    CostCenterSerializer,
)
from apps.it_financial_management.services import ITFinancialService
from apps.service_desk.tenancy import get_active_company, require_company


class CostCenterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CostCenterSerializer
    search_fields = ("code", "name")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = CostCenter.objects.select_related("department", "owner")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))

    @action(detail=True, methods=["get"])
    def budget_status(self, request, pk=None):
        cc = self.get_object()
        year = int(request.query_params.get("year") or timezone.localdate().year)
        return Response(ITFinancialService.budget_vs_actual(cc, year))


class BudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BudgetSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = Budget.objects.select_related("cost_center")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))


class ChargebackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ChargebackEntrySerializer
    filterset_fields = ("cost_center", "category", "posted_on")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ChargebackEntry.objects.select_related("cost_center", "ticket", "created_by")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            company=require_company(self.request), created_by=self.request.user
        )


class FinanceBootstrapAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = require_company(request)
        year = timezone.localdate().year
        it = ITFinancialService.ensure_cost_center(company, "it-ops", "IT Operations")
        ITFinancialService.set_budget(it, year, amount="1500000.00")
        return Response(
            {
                "cost_center": CostCenterSerializer(it).data,
                "status": ITFinancialService.budget_vs_actual(it, year),
            },
            status=status.HTTP_201_CREATED,
        )
