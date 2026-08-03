from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.network_discovery.models import DiscoveryScan
from apps.network_discovery.serializers import (
    DiscoveryScanCreateSerializer,
    DiscoveryScanSerializer,
)
from apps.network_discovery.services import NetworkDiscoveryService
from apps.service_desk.tenancy import get_active_company, require_company


class DiscoveryScanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DiscoveryScanSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = DiscoveryScan.objects.prefetch_related("hosts")
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        ser = DiscoveryScanCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        scan = NetworkDiscoveryService.create_scan(
            company,
            name=ser.validated_data["name"],
            cidr=ser.validated_data["cidr"],
            created_by=request.user,
        )
        if ser.validated_data.get("run_immediately", True):
            NetworkDiscoveryService.run_scan(scan)
            scan.refresh_from_db()
        return Response(DiscoveryScanSerializer(scan).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        scan = self.get_object()
        NetworkDiscoveryService.run_scan(scan)
        scan.refresh_from_db()
        return Response(DiscoveryScanSerializer(scan).data)
