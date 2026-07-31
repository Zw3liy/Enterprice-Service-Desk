from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.procurement.models import PurchaseOrder, PurchaseRequest
from apps.procurement.serializers import (
    PurchaseOrderSerializer,
    PurchaseRequestCreateSerializer,
    PurchaseRequestSerializer,
)
from apps.procurement.services import ProcurementService
from apps.service_desk.tenancy import get_active_company, require_company
from apps.vendor_management.models import Vendor

User = get_user_model()


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseRequestSerializer
    filterset_fields = ("state",)
    search_fields = ("number", "title")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = PurchaseRequest.objects.prefetch_related("lines").select_related(
            "requester", "approver"
        )
        if company:
            qs = qs.filter(company=company)
        return qs

    def create(self, request, *args, **kwargs):
        ser = PurchaseRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        data = ser.validated_data
        pr = ProcurementService.create_request(
            company,
            title=data["title"],
            justification=data.get("justification") or "",
            requester=request.user,
            lines=data.get("lines") or [],
            needed_by=data.get("needed_by"),
            currency=data.get("currency") or "ZAR",
        )
        return Response(
            PurchaseRequestSerializer(pr).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        pr = self.get_object()
        ProcurementService.submit(pr, actor=request.user)
        return Response(PurchaseRequestSerializer(pr).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Staff only"}, status=403)
        pr = self.get_object()
        approved = bool(request.data.get("approved"))
        ProcurementService.decide(
            pr,
            approved=approved,
            actor=request.user,
            note=request.data.get("note") or "",
        )
        return Response(PurchaseRequestSerializer(pr).data)

    @action(detail=True, methods=["post"])
    def create_po(self, request, pk=None):
        pr = self.get_object()
        vendor = None
        if request.data.get("vendor_id"):
            vendor = get_object_or_404(
                Vendor, pk=request.data["vendor_id"], company=pr.company
            )
        try:
            po = ProcurementService.create_po_from_request(
                pr, vendor=vendor, user=request.user
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseOrderSerializer
    filterset_fields = ("state", "vendor")
    search_fields = ("number", "notes")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = PurchaseOrder.objects.select_related(
            "vendor", "purchase_request", "created_by"
        )
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            company=require_company(self.request), created_by=self.request.user
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        po = self.get_object()
        ProcurementService.send_po(po, actor=request.user)
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        po = self.get_object()
        ProcurementService.receive_po(
            po,
            actor=request.user,
            receive_to_inventory=bool(request.data.get("to_inventory", True)),
        )
        return Response(PurchaseOrderSerializer(po).data)
