from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.service_desk.tenancy import get_active_company, require_company
from apps.warranty.models import WarrantyRecord
from apps.warranty.serializers import WarrantyRecordSerializer
from apps.warranty.services import WarrantyService


class WarrantyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WarrantyRecordSerializer
    filterset_fields = ("status", "asset", "vendor")
    search_fields = ("contract_number", "provider_name", "asset__asset_tag")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = WarrantyRecord.objects.select_related("asset", "vendor", "company")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        company = require_company(request)
        days = int(request.query_params.get("days") or 60)
        qs = WarrantyService.expiring(company, within_days=days)
        return Response(WarrantyRecordSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"])
    def refresh_expired(self, request):
        company = require_company(request)
        count = WarrantyService.refresh_expired(company)
        return Response({"expired": count})
