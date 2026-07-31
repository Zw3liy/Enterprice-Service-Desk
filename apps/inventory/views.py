from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import StockItem, StockLevel, StockMovement, Warehouse
from apps.inventory.serializers import (
    StockItemSerializer,
    StockLevelSerializer,
    StockMoveSerializer,
    StockMovementSerializer,
    WarehouseSerializer,
)
from apps.inventory.services import InventoryService
from apps.service_desk.tenancy import get_active_company, require_company


class WarehouseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WarehouseSerializer
    search_fields = ("code", "name", "location")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = Warehouse.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))


class StockItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StockItemSerializer
    search_fields = ("sku", "name")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = StockItem.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StockMovementSerializer
    filterset_fields = ("warehouse", "item", "movement_type")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = StockMovement.objects.select_related("warehouse", "item", "created_by")
        if company:
            qs = qs.filter(company=company)
        return qs


class StockMoveAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = StockMoveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        data = ser.validated_data
        warehouse = get_object_or_404(
            Warehouse, pk=data["warehouse_id"], company=company
        )
        item = get_object_or_404(StockItem, pk=data["item_id"], company=company)
        try:
            movement = InventoryService.move(
                company=company,
                warehouse=warehouse,
                item=item,
                movement_type=data["movement_type"],
                quantity=data["quantity"],
                reference=data.get("reference") or "",
                notes=data.get("notes") or "",
                user=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED
        )


class InventoryReorderAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = require_company(request)
        rows = InventoryService.below_reorder(company)
        return Response(
            [
                {
                    "sku": r["item"].sku,
                    "name": r["item"].name,
                    "on_hand": r["on_hand"],
                    "reorder_level": r["reorder_level"],
                }
                for r in rows
            ]
        )
