from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.business_rules.models import BusinessRule
from apps.business_rules.serializers import BusinessRuleSerializer
from apps.service_desk.tenancy import get_active_company, require_company


class BusinessRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BusinessRuleSerializer
    filterset_fields = ("scope", "is_active")
    search_fields = ("name", "code")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = BusinessRule.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))
