from rest_framework import serializers

from apps.event_engine.models import DomainEvent


class DomainEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainEvent
        fields = (
            "id",
            "company",
            "event_type",
            "aggregate_type",
            "aggregate_id",
            "payload",
            "metadata",
            "correlation_id",
            "created_at",
        )
