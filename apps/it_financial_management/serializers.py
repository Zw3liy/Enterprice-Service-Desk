from rest_framework import serializers

from apps.it_financial_management.models import Budget, ChargebackEntry, CostCenter


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = (
            "id",
            "company",
            "code",
            "name",
            "department",
            "owner",
            "is_active",
            "created_at",
        )


class BudgetSerializer(serializers.ModelSerializer):
    cost_center_code = serializers.CharField(source="cost_center.code", read_only=True)

    class Meta:
        model = Budget
        fields = (
            "id",
            "company",
            "cost_center",
            "cost_center_code",
            "fiscal_year",
            "amount",
            "currency",
            "notes",
            "created_at",
        )


class ChargebackEntrySerializer(serializers.ModelSerializer):
    cost_center_code = serializers.CharField(source="cost_center.code", read_only=True)

    class Meta:
        model = ChargebackEntry
        fields = (
            "id",
            "company",
            "cost_center",
            "cost_center_code",
            "category",
            "description",
            "amount",
            "currency",
            "ticket",
            "posted_on",
            "created_by",
            "created_at",
        )
        read_only_fields = ("created_by", "created_at")
