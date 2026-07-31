from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.scheduled_reports.models import ReportRun, ScheduledReport
from apps.scheduled_reports.serializers import ReportRunSerializer, ScheduledReportSerializer
from apps.scheduled_reports.services import ScheduledReportService
from apps.service_desk.tenancy import get_active_company, require_company


class ScheduledReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ScheduledReportSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ScheduledReport.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        report = serializer.save(
            company=require_company(self.request), created_by=self.request.user
        )
        ScheduledReportService.schedule_next(report)

    @action(detail=True, methods=["post"])
    def run_now(self, request, pk=None):
        report = self.get_object()
        run = ScheduledReportService.run(report)
        return Response(ReportRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ReportRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportRunSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ReportRun.objects.select_related("report")
        if company:
            qs = qs.filter(report__company=company)
        return qs
