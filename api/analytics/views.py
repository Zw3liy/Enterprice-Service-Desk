from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.service_desk.reporting.exports import tickets_csv
from apps.service_desk.services.dashboard_service import DashboardService
from apps.service_desk.tenancy import get_active_company


class AnalyticsDashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        return Response(DashboardService.summary(company=company, user=request.user))


class AnalyticsExportAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        from apps.service_desk.models import Ticket

        qs = Ticket.objects.all()
        if company:
            qs = qs.filter(company=company)
        content = tickets_csv(qs)
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tickets.csv"'
        return response
