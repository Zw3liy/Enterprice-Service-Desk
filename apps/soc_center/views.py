from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.service_desk.tenancy import get_active_company, require_company
from apps.soc_center.models import PlaybookRun, SecurityIncident, SOCPlaybook
from apps.soc_center.serializers import (
    PlaybookRunSerializer,
    SecurityIncidentCreateSerializer,
    SecurityIncidentSerializer,
    SOCPlaybookSerializer,
)
from apps.soc_center.services import SOCService


class SecurityIncidentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SecurityIncidentSerializer
    filterset_fields = ("severity", "state", "category", "source")
    search_fields = ("title", "summary")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = SecurityIncident.objects.select_related("ticket", "assignee", "company")
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        ser = SecurityIncidentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        data = ser.validated_data
        si = SOCService.open_incident(
            company,
            title=data["title"],
            summary=data.get("summary") or "",
            severity=data.get("severity"),
            category=data.get("category") or "general",
            source=data.get("source") or "manual",
            iocs=data.get("iocs") or [],
            mitre_tactics=data.get("mitre_tactics") or [],
            create_ticket=data.get("create_ticket", True),
            actor=request.user,
        )
        return Response(SecurityIncidentSerializer(si).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        incident = self.get_object()
        state = request.data.get("state")
        if state not in dict(SecurityIncident.State.choices):
            return Response({"detail": "Invalid state"}, status=400)
        SOCService.transition(incident, state, actor=request.user)
        return Response(SecurityIncidentSerializer(incident).data)

    @action(detail=True, methods=["post"])
    def run_playbook(self, request, pk=None):
        incident = self.get_object()
        playbook_id = request.data.get("playbook_id")
        playbook = get_object_or_404(
            SOCPlaybook, pk=playbook_id, company=incident.company, is_active=True
        )
        run = SOCService.start_playbook(incident, playbook, user=request.user)
        return Response(PlaybookRunSerializer(run).data, status=status.HTTP_201_CREATED)


class SOCPlaybookViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SOCPlaybookSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = SOCPlaybook.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        company = require_company(self.request)
        SOCService.ensure_default_playbooks(company)
        serializer.save(company=company)

    @action(detail=False, methods=["post"])
    def bootstrap(self, request):
        company = require_company(request)
        SOCService.ensure_default_playbooks(company)
        qs = SOCPlaybook.objects.filter(company=company)
        return Response(SOCPlaybookSerializer(qs, many=True).data)


class PlaybookRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PlaybookRunSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = PlaybookRun.objects.select_related("playbook", "security_incident")
        if company:
            qs = qs.filter(security_incident__company=company)
        return qs

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        run = self.get_object()
        SOCService.advance_playbook(run, note=request.data.get("note") or "", user=request.user)
        return Response(PlaybookRunSerializer(run).data)
