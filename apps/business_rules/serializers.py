from rest_framework import serializers

from apps.business_rules.models import BusinessRule


class BusinessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessRule
        fields = (
            "id",
            "company",
            "name",
            "code",
            "scope",
            "description",
            "conditions",
            "actions",
            "priority",
            "is_active",
            "stop_on_match",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
