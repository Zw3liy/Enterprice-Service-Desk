from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.service_desk.models import WebhookEndpoint
from apps.service_desk.tenancy import get_active_company, require_company
from apps.webhooks.models import WebhookDelivery
from apps.webhooks.serializers import (
    WebhookDeliverySerializer,
    WebhookEndpointSerializer,
    WebhookTestSerializer,
)
from apps.webhooks.services import WebhookService


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookEndpointSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = WebhookEndpoint.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        endpoint = self.get_object()
        ser = WebhookTestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # Temporarily ensure this endpoint is targeted via event filter
        deliveries = WebhookService.dispatch(
            endpoint.company,
            ser.validated_data.get("event") or "test.ping",
            ser.validated_data.get("payload") or {"ok": True},
        )
        mine = [d for d in deliveries if d.endpoint_id == endpoint.pk]
        return Response(
            WebhookDeliverySerializer(mine, many=True).data,
            status=status.HTTP_200_OK,
        )


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookDeliverySerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = WebhookDelivery.objects.select_related("endpoint", "company")
        if company:
            qs = qs.filter(company=company)
        return qs