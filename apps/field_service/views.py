from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.field_service.models import WorkOrder
from apps.field_service.serializers import WorkOrderCreateSerializer, WorkOrderSerializer
from apps.field_service.services import FieldService
from apps.service_desk.models import Ticket
from apps.service_desk.tenancy import get_active_company

User = get_user_model()


class WorkOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkOrderSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = WorkOrder.objects.select_related("ticket", "technician", "company")
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        ser = WorkOrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ticket = get_object_or_404(Ticket, pk=ser.validated_data["ticket_id"])
        tech = None
        if ser.validated_data.get("technician_id"):
            tech = get_object_or_404(User, pk=ser.validated_data["technician_id"])
        wo = FieldService.create_work_order(
            ticket,
            title=ser.validated_data.get("title") or "",
            description=ser.validated_data.get("description") or "",
            location=ser.validated_data.get("location") or "",
            technician=tech,
            scheduled_start=ser.validated_data.get("scheduled_start"),
            scheduled_end=ser.validated_data.get("scheduled_end"),
            actor=request.user,
        )
        return Response(WorkOrderSerializer(wo).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def dispatch_order(self, request, pk=None):
        wo = self.get_object()
        tech = None
        if request.data.get("technician_id"):
            tech = get_object_or_404(User, pk=request.data["technician_id"])
        FieldService.dispatch(wo, technician=tech, actor=request.user)
        return Response(WorkOrderSerializer(wo).data)

    @action(detail=True, methods=["post"])
    def check_in(self, request, pk=None):
        wo = self.get_object()
        FieldService.check_in(wo, actor=request.user)
        return Response(WorkOrderSerializer(wo).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        wo = self.get_object()
        FieldService.complete(
            wo, notes=request.data.get("notes") or "", actor=request.user
        )
        return Response(WorkOrderSerializer(wo).data)
