from rest_framework import serializers

from apps.integrations.models import IntegrationConnection


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationConnection
        fields = (
            "id",
            "company",
            "provider",
            "name",
            "state",
            "config",
            "last_synced_at",
            "last_error",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "state",
            "last_synced_at",
            "last_error",
            "created_by",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"config": {"write_only": False}}


class IntegrationUpsertSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=IntegrationConnection.Provider.choices)
    name = serializers.CharField(max_length=160)
    config = serializers.DictField(required=False, default=dict)
