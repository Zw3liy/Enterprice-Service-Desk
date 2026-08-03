from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.audit import log_integration
from apps.integrations.connectors import ConnectorRegistry
from apps.integrations.models import IntegrationConnection
from apps.integrations.serializers import (
    IntegrationConnectionSerializer,
    IntegrationUpsertSerializer,
)
from apps.service_desk.tenancy import get_active_company, require_company


class IntegrationConnectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = IntegrationConnectionSerializer
    filterset_fields = ("provider", "state")
    search_fields = ("name",)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = IntegrationConnection.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        ser = IntegrationUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        conn = ConnectorRegistry.upsert(
            company,
            provider=ser.validated_data["provider"],
            name=ser.validated_data["name"],
            config=ser.validated_data.get("config") or {},
            user=request.user,
        )
        log_integration(
            company,
            "configured",
            message=conn.name,
            actor=request.user,
            metadata={"provider": conn.provider},
        )
        return Response(
            IntegrationConnectionSerializer(conn).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        conn = self.get_object()
        result = ConnectorRegistry.test_connection(conn)
        return Response(result, status=200 if result.get("ok") else 400)


class IntegrationProvidersAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            [
                {"value": v, "label": l}
                for v, l in IntegrationConnection.Provider.choices
            ]
        )
