from rest_framework import serializers

from apps.customer_portal.models import PortalAnnouncement, PortalProfile
from apps.service_desk.api.serializers import (
    KnowledgeArticleSerializer,
    RequestTypeSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
)


class PortalProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = PortalProfile
        fields = (
            "id",
            "user",
            "username",
            "company",
            "display_name",
            "department_name",
            "notify_email",
            "notify_in_app",
            "preferred_language",
        )
        read_only_fields = ("user", "company")


class PortalAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalAnnouncement
        fields = (
            "id",
            "company",
            "title",
            "body",
            "is_active",
            "starts_at",
            "ends_at",
            "priority",
            "created_at",
        )


class PortalRequestCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    request_type_id = serializers.IntegerField(required=False, allow_null=True)


class PortalTicketSerializer(TicketListSerializer):
    pass


class PortalTicketDetailSerializer(TicketDetailSerializer):
    pass


class PortalCatalogSerializer(RequestTypeSerializer):
    pass


class PortalKnowledgeSerializer(KnowledgeArticleSerializer):
    pass