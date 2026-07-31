from rest_framework import serializers

from apps.change_management.models import CABMeeting, ChangeApproval, ChangeRequest
from apps.service_desk.api.serializers import TicketListSerializer


class ChangeRequestSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source="ticket.ticket_number", read_only=True)
    title = serializers.CharField(source="ticket.title", read_only=True)

    class Meta:
        model = ChangeRequest
        fields = (
            "id",
            "ticket",
            "ticket_number",
            "title",
            "company",
            "change_type",
            "risk",
            "state",
            "justification",
            "implementation_plan",
            "rollback_plan",
            "test_plan",
            "scheduled_start",
            "scheduled_end",
            "actual_start",
            "actual_end",
            "cab_required",
            "requester",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "actual_start", "actual_end")


class ChangeCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    change_type = serializers.ChoiceField(
        choices=ChangeRequest.ChangeType.choices, default=ChangeRequest.ChangeType.NORMAL
    )
    risk = serializers.ChoiceField(
        choices=ChangeRequest.Risk.choices, default=ChangeRequest.Risk.MEDIUM
    )
    justification = serializers.CharField(required=False, allow_blank=True, default="")
    implementation_plan = serializers.CharField(required=False, allow_blank=True, default="")
    rollback_plan = serializers.CharField(required=False, allow_blank=True, default="")
    test_plan = serializers.CharField(required=False, allow_blank=True, default="")
    scheduled_start = serializers.DateTimeField(required=False, allow_null=True)
    scheduled_end = serializers.DateTimeField(required=False, allow_null=True)


class ChangeDecisionSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ChangeApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeApproval
        fields = (
            "id",
            "change",
            "approver",
            "decision",
            "comment",
            "decided_at",
            "created_at",
        )


class CABMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CABMeeting
        fields = (
            "id",
            "company",
            "title",
            "scheduled_at",
            "location",
            "chair",
            "members",
            "changes",
            "minutes",
            "is_closed",
            "created_at",
        )


class ChangeTicketSerializer(TicketListSerializer):
    pass