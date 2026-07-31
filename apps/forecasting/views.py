from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.forecasting.serializers import ForecastQuerySerializer
from apps.forecasting.services import ForecastingService
from apps.service_desk.tenancy import require_company


class TicketForecastAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = ForecastQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        data = ForecastingService.ticket_volume_forecast(
            company,
            history_days=ser.validated_data.get("history_days") or 28,
            horizon_days=ser.validated_data.get("horizon_days") or 7,
        )
        return Response(data)


class StaffingForecastAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = require_company(request)
        tpa = float(request.query_params.get("tickets_per_agent_per_day") or 8)
        return Response(ForecastingService.staffing_suggestion(company, tpa))
