from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.monitoring_engine.models import MonitoringAlert
from apps.monitoring_engine.serializers import (
    MonitoringAlertSerializer,
    MonitoringIngestSerializer,
)
from apps.monitoring_engine.services import MonitoringService
from apps.service_desk.tenancy import get_active_company, require_company


class MonitoringAlertViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MonitoringAlertSerializer
    filterset_fields = ("severity", "state", "source")
    search_fields = ("title", "host", "service", "external_id")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = MonitoringAlert.objects.select_related("ticket", "company")
        if company:
            qs = qs.filter(company=company)
        return qs

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        MonitoringService.resolve(alert, actor=request.user)
        return Response(MonitoringAlertSerializer(alert).data)


class MonitoringIngestAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = MonitoringIngestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        data = ser.validated_data
        alert = MonitoringService.ingest(
            company,
            title=data["title"],
            description=data.get("description") or "",
            severity=data.get("severity"),
            source=data.get("source") or "generic",
            external_id=data.get("external_id") or "",
            host=data.get("host") or "",
            service=data.get("service") or "",
            payload=data.get("payload") or {},
            open_incident=data.get("open_incident", True),
            actor=request.user,
        )
        return Response(MonitoringAlertSerializer(alert).data, status=status.HTTP_201_CREATED)
