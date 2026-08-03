from rest_framework import serializers

from apps.release_management.models import Release, ReleaseTask


class ReleaseTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseTask
        fields = (
            "id",
            "release",
            "title",
            "description",
            "assignee",
            "state",
            "sequence",
            "due_at",
            "created_at",
            "updated_at",
        )


class ReleaseSerializer(serializers.ModelSerializer):
    tasks = ReleaseTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Release
        fields = (
            "id",
            "company",
            "name",
            "version",
            "description",
            "state",
            "manager",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
            "changes",
            "deployment_notes",
            "rollback_notes",
            "tasks",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("actual_start", "actual_end", "created_at", "updated_at")


class ReleaseCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    version = serializers.CharField(max_length=60)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    planned_start = serializers.DateTimeField(required=False, allow_null=True)
    planned_end = serializers.DateTimeField(required=False, allow_null=True)
    change_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )