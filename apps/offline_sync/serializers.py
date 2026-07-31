from rest_framework import serializers

from apps.offline_sync.models import OfflineMutation, SyncCursor


class SyncCursorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncCursor
        fields = (
            "device_id",
            "last_pulled_at",
            "last_pushed_at",
            "cursor_token",
            "updated_at",
        )


class OfflineMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineMutation
        fields = (
            "id",
            "client_mutation_id",
            "entity_type",
            "entity_id",
            "operation",
            "payload",
            "state",
            "error_message",
            "applied_at",
            "result",
            "created_at",
        )


class SyncPullSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=120)
    since = serializers.DateTimeField(required=False, allow_null=True)


class SyncPushSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=120)
    mutations = serializers.ListField(child=serializers.DictField(), allow_empty=True)
