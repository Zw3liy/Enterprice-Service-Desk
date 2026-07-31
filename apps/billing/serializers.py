from rest_framework import serializers

from apps.billing.models import Invoice, Plan, Subscription, UsageRecord


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "code",
            "name",
            "tier",
            "description",
            "price_monthly",
            "price_yearly",
            "currency",
            "max_agents",
            "max_tickets_per_month",
            "max_assets",
            "features",
            "is_active",
            "sort_order",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_detail = PlanSerializer(source="plan", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "company",
            "company_name",
            "plan",
            "plan_detail",
            "status",
            "seats",
            "billing_email",
            "trial_ends_at",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "external_customer_id",
            "external_subscription_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class SubscribeSerializer(serializers.Serializer):
    plan_code = serializers.SlugField()
    seats = serializers.IntegerField(min_value=1, default=1)
    trial_days = serializers.IntegerField(min_value=0, default=14)
    billing_email = serializers.EmailField(required=False, allow_blank=True, default="")


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = (
            "id",
            "company",
            "metric",
            "quantity",
            "period_start",
            "period_end",
            "metadata",
            "created_at",
        )


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "company",
            "subscription",
            "number",
            "status",
            "currency",
            "subtotal",
            "tax",
            "total",
            "period_start",
            "period_end",
            "due_date",
            "paid_at",
            "line_items",
            "notes",
            "created_at",
        )
        read_only_fields = ("number", "created_at", "paid_at")