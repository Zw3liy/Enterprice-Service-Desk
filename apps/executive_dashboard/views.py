from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.executive_dashboard.services import ExecutiveDashboardService
from apps.service_desk.tenancy import get_active_company


@login_required
def executive_home(request):
    company = get_active_company(request)
    pack = ExecutiveDashboardService.board_pack(company=company, user=request.user)
    return render(
        request,
        "executive_dashboard/home.html",
        {
            "title": "Executive Dashboard",
            "pack": pack,
            "kpis": pack.get("kpis") or {},
            "portfolio": pack.get("portfolio") or {},
            "sla": pack.get("sla") or {},
            "agents": pack.get("agents") or [],
            "forecast": pack.get("forecast") or [],
            "staffing": pack.get("staffing") or {},
        },
    )


class ExecutiveBoardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        return Response(
            ExecutiveDashboardService.board_pack(company=company, user=request.user)
        )
