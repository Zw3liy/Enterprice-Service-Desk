from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.form_builder.models import FormDefinition, FormSubmission
from apps.form_builder.serializers import (
    FormDefinitionSerializer,
    FormSubmissionSerializer,
    FormSubmitSerializer,
)
from apps.form_builder.services import FormBuilderService
from apps.service_desk.tenancy import get_active_company, require_company


class FormDefinitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FormDefinitionSerializer
    lookup_field = "code"
    search_fields = ("name", "code")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = FormDefinition.objects.filter(is_active=True)
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        company = require_company(self.request)
        schema = serializer.validated_data.get("schema") or []
        FormBuilderService.validate_schema(schema)
        serializer.save(company=company)

    @action(detail=True, methods=["post"])
    def submit(self, request, code=None):
        form = self.get_object()
        ser = FormSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            submission = FormBuilderService.submit(
                form,
                ser.validated_data["values"],
                user=request.user,
                create_ticket=ser.validated_data.get("create_ticket", True),
                title=ser.validated_data.get("title") or "",
            )
        except ValidationError as exc:
            return Response({"errors": getattr(exc, "message_dict", str(exc))}, status=400)
        return Response(
            FormSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED
        )


class FormSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FormSubmissionSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = FormSubmission.objects.select_related("form", "ticket", "submitted_by")
        if company:
            qs = qs.filter(company=company)
        return qs
