from rest_framework import serializers

from apps.procurement.models import PurchaseOrder, PurchaseRequest, PurchaseRequestLine


class PurchaseRequestLineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseRequestLine
        fields = (
            "id",
            "description",
            "quantity",
            "unit_price",
            "sku",
            "line_total",
        )


class PurchaseRequestSerializer(serializers.ModelSerializer):
    lines = PurchaseRequestLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseRequest
        fields = (
            "id",
            "company",
            "number",
            "title",
            "justification",
            "state",
            "requester",
            "approver",
            "needed_by",
            "total_estimate",
            "currency",
            "lines",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("number", "total_estimate", "created_at", "updated_at")


class PurchaseRequestCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    justification = serializers.CharField(required=False, allow_blank=True, default="")
    needed_by = serializers.DateField(required=False, allow_null=True)
    currency = serializers.CharField(required=False, default="ZAR")
    lines = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = (
            "id",
            "company",
            "purchase_request",
            "vendor",
            "number",
            "state",
            "currency",
            "total",
            "ordered_at",
            "notes",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("number", "ordered_at", "created_by", "created_at", "updated_at")
