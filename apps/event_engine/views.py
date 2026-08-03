from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.event_engine.models import DomainEvent
from apps.event_engine.serializers import DomainEventSerializer
from apps.service_desk.tenancy import get_active_company


class DomainEventViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DomainEventSerializer
    filterset_fields = ("event_type", "aggregate_type", "aggregate_id", "correlation_id")
    search_fields = ("event_type", "aggregate_id", "correlation_id")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = DomainEvent.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs
