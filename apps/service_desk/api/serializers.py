"""REST serializers for the Service Desk API."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.service_desk.models import (
    Asset,
    AuditLog,
    Category,
    Company,
    Contact,
    CustomerFeedback,
    Department,
    KnowledgeArticle,
    Notification,
    Priority,
    Queue,
    RequestType,
    SLA,
    Status,
    Ticket,
    TicketAttachment,
    TicketComment,
    WorkLog,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_staff")


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "id",
            "uuid" if hasattr(Company, "uuid") else "id",
            "name",
            "slug",
            "is_active",
            "timezone",
            "primary_email",
            "created_at",
        )
        # uuid may not exist on Company — handle below


# Fix Company serializer fields cleanly
CompanySerializer.Meta.fields = (
    "id",
    "name",
    "slug",
    "is_active",
    "timezone",
    "primary_email",
    "created_at",
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = (
            "id",
            "company",
            "name",
            "code",
            "email",
            "ticket_counter",
            "is_active",
        )


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = (
            "id",
            "company",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "job_title",
            "vip",
            "is_active",
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "company", "parent", "name", "code", "description", "is_active")


class PrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Priority
        fields = (
            "id",
            "company",
            "name",
            "code",
            "rank",
            "colour",
            "impact",
            "urgency",
            "is_active",
        )


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = (
            "id",
            "company",
            "name",
            "code",
            "rank",
            "category",
            "is_terminal",
            "colour",
            "is_active",
        )


class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = (
            "id",
            "company",
            "department",
            "name",
            "code",
            "description",
            "is_active",
            "members",
        )


class RequestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestType
        fields = (
            "id",
            "department",
            "name",
            "code",
            "description",
            "is_active",
            "default_priority",
            "default_queue",
            "sla",
        )


class SLASerializer(serializers.ModelSerializer):
    class Meta:
        model = SLA
        fields = (
            "id",
            "company",
            "name",
            "priority",
            "response_minutes",
            "resolution_minutes",
            "business_hours_only",
            "is_active",
            "description",
        )


class TicketCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = TicketComment
        fields = (
            "id",
            "ticket",
            "author",
            "body",
            "is_internal",
            "is_system",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("author", "is_system", "created_at", "updated_at")


class WorkLogSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = WorkLog
        fields = (
            "id",
            "ticket",
            "author",
            "description",
            "minutes_spent",
            "performed_at",
            "is_billable",
            "created_at",
        )
        read_only_fields = ("author", "created_at")


class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = (
            "id",
            "ticket",
            "file",
            "original_name",
            "content_type",
            "size_bytes",
            "uploaded_by",
            "created_at",
        )
        read_only_fields = (
            "original_name",
            "content_type",
            "size_bytes",
            "uploaded_by",
            "created_at",
        )


class TicketListSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source="status.name", read_only=True, default=None)
    priority_name = serializers.CharField(source="priority.name", read_only=True, default=None)
    assignee_name = serializers.CharField(
        source="assignee.get_username", read_only=True, default=None
    )

    class Meta:
        model = Ticket
        fields = (
            "id",
            "uuid",
            "ticket_number",
            "title",
            "ticket_type",
            "channel",
            "status",
            "status_name",
            "priority",
            "priority_name",
            "queue",
            "assignee",
            "assignee_name",
            "company",
            "department",
            "is_major_incident",
            "sla_response_breached",
            "sla_resolution_breached",
            "response_due_at",
            "resolution_due_at",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
        )


class TicketDetailSerializer(TicketListSerializer):
    comments = TicketCommentSerializer(many=True, read_only=True)
    work_logs = WorkLogSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    requester = ContactSerializer(read_only=True)
    ai_summary = serializers.CharField(read_only=True)
    ai_category_suggestion = serializers.CharField(read_only=True)
    sentiment_score = serializers.FloatField(read_only=True)

    class Meta(TicketListSerializer.Meta):
        fields = TicketListSerializer.Meta.fields + (
            "description",
            "request_type",
            "category",
            "sla",
            "requester",
            "requester_user",
            "custom_field_values",
            "tags",
            "impact",
            "urgency",
            "parent",
            "assets",
            "first_response_at",
            "ai_summary",
            "ai_category_suggestion",
            "sentiment_score",
            "comments",
            "work_logs",
            "attachments",
        )


class TicketCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    ticket_type = serializers.ChoiceField(
        choices=Ticket.TicketType.choices, default=Ticket.TicketType.INCIDENT
    )
    channel = serializers.ChoiceField(
        choices=Ticket.Channel.choices, default=Ticket.Channel.API
    )
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), required=False, allow_null=True
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    request_type = serializers.PrimaryKeyRelatedField(
        queryset=RequestType.objects.all(), required=False, allow_null=True
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )
    priority = serializers.PrimaryKeyRelatedField(
        queryset=Priority.objects.all(), required=False, allow_null=True
    )
    queue = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, allow_null=True
    )
    status = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), required=False, allow_null=True
    )
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True
    )
    custom_field_values = serializers.DictField(required=False, default=dict)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, default=list
    )
    impact = serializers.IntegerField(min_value=1, max_value=5, default=3)
    urgency = serializers.IntegerField(min_value=1, max_value=5, default=3)
    auto_assign = serializers.BooleanField(default=False)
    asset_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class TicketUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    ticket_type = serializers.ChoiceField(
        choices=Ticket.TicketType.choices, required=False
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )
    priority = serializers.PrimaryKeyRelatedField(
        queryset=Priority.objects.all(), required=False, allow_null=True
    )
    status = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), required=False, allow_null=True
    )
    queue = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, allow_null=True
    )
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False
    )
    custom_field_values = serializers.DictField(required=False)
    impact = serializers.IntegerField(min_value=1, max_value=5, required=False)
    urgency = serializers.IntegerField(min_value=1, max_value=5, required=False)
    is_major_incident = serializers.BooleanField(required=False)


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    is_internal = serializers.BooleanField(default=False)


class AssignSerializer(serializers.Serializer):
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True
    )
    queue = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, allow_null=True
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")
    auto_assign = serializers.BooleanField(default=False)


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = (
            "id",
            "uuid",
            "company",
            "name",
            "asset_tag",
            "asset_type",
            "lifecycle_state",
            "serial_number",
            "manufacturer",
            "model_name",
            "location",
            "department",
            "owner",
            "is_active",
            "configuration",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("uuid", "created_at", "updated_at")


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArticle
        fields = (
            "id",
            "company",
            "category",
            "title",
            "slug",
            "summary",
            "body",
            "is_published",
            "is_internal",
            "published_at",
            "author",
            "view_count",
            "helpful_yes",
            "helpful_no",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "slug",
            "published_at",
            "author",
            "view_count",
            "helpful_yes",
            "helpful_no",
            "created_at",
            "updated_at",
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "subject",
            "body",
            "channel",
            "status",
            "ticket",
            "created_at",
            "read_at",
            "sent_at",
        )


class AuditLogSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "message",
            "ticket",
            "company",
            "actor",
            "object_type",
            "object_id",
            "metadata",
            "ip_address",
            "created_at",
        )


class AIClassifySerializer(serializers.Serializer):
    text = serializers.CharField()


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerFeedback
        fields = ("id", "ticket", "rating", "comment", "submitted_at")
        read_only_fields = ("submitted_at",)
