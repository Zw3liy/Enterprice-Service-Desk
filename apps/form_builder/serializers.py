from rest_framework import serializers

from apps.form_builder.models import FormDefinition, FormSubmission


class FormDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormDefinition
        fields = (
            "id",
            "company",
            "name",
            "code",
            "description",
            "request_type",
            "schema",
            "is_active",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class FormSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        fields = (
            "id",
            "form",
            "company",
            "values",
            "submitted_by",
            "ticket",
            "created_at",
        )
        read_only_fields = ("submitted_by", "ticket", "created_at")


class FormSubmitSerializer(serializers.Serializer):
    values = serializers.DictField()
    title = serializers.CharField(required=False, allow_blank=True, default="")
    create_ticket = serializers.BooleanField(default=True)
