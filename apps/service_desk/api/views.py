"""DRF viewsets and API endpoints."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.service_desk.api.serializers import (
    AIClassifySerializer,
    AssetSerializer,
    AssignSerializer,
    AuditLogSerializer,
    CategorySerializer,
    CommentCreateSerializer,
    CompanySerializer,
    DepartmentSerializer,
    FeedbackSerializer,
    KnowledgeArticleSerializer,
    NotificationSerializer,
    PrioritySerializer,
    QueueSerializer,
    RequestTypeSerializer,
    SLASerializer,
    StatusSerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
    TicketUpdateSerializer,
    WorkLogSerializer,
)
from apps.service_desk.models import (
    Asset,
    AuditLog,
    Category,
    Company,
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
)
from apps.service_desk.services.ai_service import AIService
from apps.service_desk.services.assignment_service import AssignmentService
from apps.service_desk.services.dashboard_service import DashboardService
from apps.service_desk.services.knowledge_service import KnowledgeService
from apps.service_desk.services.sla_service import SLAService
from apps.service_desk.services.ticket_service import TicketService
from apps.service_desk.tenancy import get_active_company


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Company.objects.filter(is_active=True)
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    search_fields = ("name", "slug")


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_active")
    search_fields = ("name", "code")

    def get_queryset(self):
        return Department.objects.select_related("company").all()


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_active", "parent")
    search_fields = ("name", "code")
    queryset = Category.objects.all()


class PriorityViewSet(viewsets.ModelViewSet):
    serializer_class = PrioritySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_active")
    queryset = Priority.objects.all()


class StatusViewSet(viewsets.ModelViewSet):
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_active", "category", "is_terminal")
    queryset = Status.objects.all()


class QueueViewSet(viewsets.ModelViewSet):
    serializer_class = QueueSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_active", "department")
    queryset = Queue.objects.prefetch_related("members").all()


class RequestTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RequestTypeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("department", "is_active")
    queryset = RequestType.objects.select_related("department").all()


class SLAViewSet(viewsets.ModelViewSet):
    serializer_class = SLASerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_active", "priority")
    queryset = SLA.objects.all()


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = (
        "company",
        "status",
        "priority",
        "queue",
        "assignee",
        "ticket_type",
        "department",
        "is_major_incident",
    )
    search_fields = ("title", "description", "ticket_number")
    ordering_fields = ("created_at", "updated_at", "priority", "resolution_due_at")
    ordering = ("-created_at",)
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return TicketService.base_queryset()

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        if self.action == "create":
            return TicketCreateSerializer
        if self.action in {"update", "partial_update"}:
            return TicketUpdateSerializer
        return TicketDetailSerializer

    def create(self, request, *args, **kwargs):
        ser = TicketCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        company = data.get("company") or get_active_company(request)
        assets = None
        asset_ids = data.pop("asset_ids", []) or []
        auto_assign = data.pop("auto_assign", False)
        if asset_ids:
            assets = Asset.objects.filter(pk__in=asset_ids)
        ticket = TicketService.create_ticket(
            title=data["title"],
            description=data.get("description") or "",
            company=company,
            department=data.get("department"),
            request_type=data.get("request_type"),
            category=data.get("category"),
            priority=data.get("priority"),
            status=data.get("status"),
            queue=data.get("queue"),
            assignee=data.get("assignee"),
            ticket_type=data.get("ticket_type") or Ticket.TicketType.INCIDENT,
            channel=data.get("channel") or Ticket.Channel.API,
            custom_field_values=data.get("custom_field_values") or {},
            tags=data.get("tags") or [],
            impact=data.get("impact") or 3,
            urgency=data.get("urgency") or 3,
            assets=assets,
            requester_user=request.user,
            actor=request.user,
            auto_assign=auto_assign,
        )
        out = TicketDetailSerializer(ticket, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        ticket = self.get_object()
        ser = TicketUpdateSerializer(data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        ticket = TicketService.update_ticket(
            ticket, actor=request.user, **ser.validated_data
        )
        return Response(TicketDetailSerializer(ticket).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        ser = CommentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        comment = TicketService.add_comment(
            ticket,
            body=ser.validated_data["body"],
            author=request.user,
            is_internal=ser.validated_data.get("is_internal") or False,
        )
        from apps.service_desk.api.serializers import TicketCommentSerializer

        return Response(
            TicketCommentSerializer(comment).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        ser = AssignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if data.get("auto_assign"):
            AssignmentService.auto_assign(ticket, assigned_by=request.user)
        else:
            AssignmentService.assign(
                ticket,
                assignee=data.get("assignee"),
                queue=data.get("queue"),
                assigned_by=request.user,
                note=data.get("note") or "",
            )
        ticket.refresh_from_db()
        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def worklogs(self, request, pk=None):
        ticket = self.get_object()
        ser = WorkLogSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        log = TicketService.add_work_log(
            ticket,
            description=ser.validated_data["description"],
            minutes_spent=ser.validated_data["minutes_spent"],
            author=request.user,
            is_billable=ser.validated_data.get("is_billable") or False,
        )
        return Response(WorkLogSerializer(log).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def feedback(self, request, pk=None):
        ticket = self.get_object()
        ser = FeedbackSerializer(data={**request.data, "ticket": ticket.pk})
        ser.is_valid(raise_exception=True)
        obj, _ = CustomerFeedback.objects.update_or_create(
            ticket=ticket,
            defaults={
                "rating": ser.validated_data["rating"],
                "comment": ser.validated_data.get("comment") or "",
            },
        )
        return Response(FeedbackSerializer(obj).data)

    @action(detail=True, methods=["get"])
    def recommendations(self, request, pk=None):
        ticket = self.get_object()
        articles = AIService.recommend_articles(ticket)
        return Response(KnowledgeArticleSerializer(articles, many=True).data)

    @action(detail=False, methods=["post"])
    def evaluate_sla(self, request):
        company = get_active_company(request)
        count = SLAService.scan_open_tickets(
            company_id=company.pk if company else None
        )
        return Response({"evaluated_breaches": count})


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "asset_type", "lifecycle_state", "is_active", "department")
    search_fields = ("name", "asset_tag", "serial_number", "location")
    queryset = Asset.objects.select_related("company", "department", "owner").all()


class KnowledgeViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeArticleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "is_published", "is_internal", "category")
    search_fields = ("title", "summary", "body", "slug")
    lookup_field = "slug"

    def get_queryset(self):
        qs = KnowledgeArticle.objects.select_related("company", "category", "author")
        if not self.request.user.is_staff:
            qs = qs.filter(is_published=True, is_internal=False)
        return qs

    def perform_create(self, serializer):
        company = serializer.validated_data.get("company") or get_active_company(
            self.request
        )
        serializer.save(author=self.request.user, company=company)

    @action(detail=True, methods=["post"])
    def view(self, request, slug=None):
        article = self.get_object()
        KnowledgeService.record_view(article)
        article.refresh_from_db()
        return Response(KnowledgeArticleSerializer(article).data)


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        note = self.get_object()
        note.mark_read()
        return Response(NotificationSerializer(note).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        qs = self.get_queryset().exclude(status=Notification.Status.READ)
        count = 0
        for note in qs:
            note.mark_read()
            count += 1
        return Response({"marked_read": count})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("company", "action", "ticket")
    search_fields = ("action", "message", "object_id")
    queryset = AuditLog.objects.select_related("actor", "ticket", "company").all()


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        return Response(DashboardService.summary(company=company, user=request.user))


class AIClassifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = AIClassifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(AIService.classify_text(ser.validated_data["text"]))


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response(
        {
            "name": "Enterprise Service Desk API",
            "version": "v1",
            "endpoints": {
                "tickets": "tickets/",
                "assets": "assets/",
                "knowledge": "knowledge/",
                "dashboard": "dashboard/",
                "ai_classify": "ai/classify/",
                "notifications": "notifications/",
                "audit": "audit/",
            },
        }
    )
