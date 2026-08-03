from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics_engine.exports.csv_export import tickets_csv
from apps.analytics_engine.exports.pdf_export import kpi_pdf
from apps.analytics_engine.reports.agent_reports import agent_workload_report
from apps.analytics_engine.reports.sla_reports import sla_report
from apps.analytics_engine.serializers import AnalyticsSnapshotSerializer
from apps.analytics_engine.services import KPIEngine, MetricsEngine
from apps.service_desk.models import Ticket
from apps.service_desk.tenancy import get_active_company, require_company


class AnalyticsKPIAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        return Response(KPIEngine.compute(company=company, user=request.user))


class AnalyticsSnapshotAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = require_company(request)
        snaps = MetricsEngine.latest(company)
        return Response(AnalyticsSnapshotSerializer(snaps, many=True).data)

    def post(self, request):
        company = require_company(request)
        snap = MetricsEngine.capture_snapshot(company)
        return Response(AnalyticsSnapshotSerializer(snap).data, status=201)


class AnalyticsSLAAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(sla_report(company=get_active_company(request)))


class AnalyticsAgentsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(agent_workload_report(company=get_active_company(request)))


class AnalyticsExportCSVAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        qs = Ticket.objects.all()
        if company:
            qs = qs.filter(company=company)
        content = tickets_csv(qs)
        resp = HttpResponse(content, content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="analytics_tickets.csv"'
        return resp


class AnalyticsExportPDFAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        summary = KPIEngine.compute(company=company, user=request.user)
        payload = kpi_pdf(summary)
        content_type = (
            "application/pdf" if payload[:4] == b"%PDF" else "text/plain"
        )
        resp = HttpResponse(payload, content_type=content_type)
        resp["Content-Disposition"] = 'attachment; filename="kpis.pdf"'
        return resp
