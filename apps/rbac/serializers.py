from rest_framework import serializers

from apps.rbac.models import RoleDefinition, UserRoleAssignment


class RoleDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleDefinition
        fields = (
            "id",
            "company",
            "code",
            "name",
            "description",
            "permissions",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserRoleAssignment
        fields = (
            "id",
            "company",
            "user",
            "username",
            "role",
            "role_code",
            "assigned_by",
            "is_active",
            "created_at",
        )
        read_only_fields = ("assigned_by", "created_at")


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role_code = serializers.SlugField()
