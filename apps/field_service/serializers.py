from rest_framework import serializers

from apps.field_service.models import WorkOrder


class WorkOrderSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source="ticket.ticket_number", read_only=True)

    class Meta:
        model = WorkOrder
        fields = (
            "id",
            "company",
            "ticket",
            "ticket_number",
            "number",
            "title",
            "description",
            "location",
            "technician",
            "state",
            "scheduled_start",
            "scheduled_end",
            "actual_start",
            "actual_end",
            "resolution_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("number", "actual_start", "actual_end", "created_at", "updated_at")


class WorkOrderCreateSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    title = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.CharField(required=False, allow_blank=True, default="")
    technician_id = serializers.IntegerField(required=False, allow_null=True)
    scheduled_start = serializers.DateTimeField(required=False, allow_null=True)
    scheduled_end = serializers.DateTimeField(required=False, allow_null=True)
