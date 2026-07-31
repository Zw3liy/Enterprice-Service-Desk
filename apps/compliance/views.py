from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.compliance.models import ComplianceEvidence, Control, ControlFramework
from apps.compliance.serializers import (
    ComplianceEvidenceSerializer,
    ControlFrameworkSerializer,
    ControlSerializer,
)
from apps.compliance.services import ComplianceService
from apps.service_desk.tenancy import get_active_company, require_company


class ControlFrameworkViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ControlFrameworkSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ControlFramework.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))

    @action(detail=True, methods=["get"])
    def scorecard(self, request, pk=None):
        fw = self.get_object()
        return Response(ComplianceService.scorecard(fw))


class ControlViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ControlSerializer
    filterset_fields = ("framework", "status", "owner")
    search_fields = ("control_id", "title")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = Control.objects.select_related("framework", "owner")
        if company:
            qs = qs.filter(framework__company=company)
        return qs


class ComplianceBootstrapAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = require_company(request)
        fw = ComplianceService.ensure_iso27001(company)
        return Response(
            {
                "framework": ControlFrameworkSerializer(fw).data,
                "scorecard": ComplianceService.scorecard(fw),
            },
            status=status.HTTP_201_CREATED,
        )


class ComplianceEvidenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ComplianceEvidenceSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ComplianceEvidence.objects.select_related("control", "collected_by")
        if company:
            qs = qs.filter(control__framework__company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(collected_by=self.request.user)
