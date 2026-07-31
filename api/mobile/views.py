from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.service_desk.api.serializers import TicketListSerializer
from apps.service_desk.services.dashboard_service import DashboardService
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company
from apps.mfa.services import MFAService


class MobileBootstrapAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        return Response(
            {
                "user": {
                    "id": request.user.pk,
                    "username": request.user.get_username(),
                    "is_staff": request.user.is_staff,
                },
                "company": {
                    "id": company.pk if company else None,
                    "name": company.name if company else None,
                    "slug": company.slug if company else None,
                },
                "mfa_enabled": MFAService.is_enabled(request.user),
                "kpis": DashboardService.summary(company=company, user=request.user),
            }
        )


class MobileTicketListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        qs = TicketService.search(
            company=company,
            open_only=request.query_params.get("open_only", "1") in {"1", "true", "yes"},
            mine_user=request.user if request.query_params.get("mine") in {"1", "true"} else None,
            query=request.query_params.get("q") or "",
        )[:50]
        return Response(TicketListSerializer(qs, many=True).data)
