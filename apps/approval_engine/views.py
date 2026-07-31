from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.approval_engine.models import ApprovalPolicy
from apps.approval_engine.process import approve, reject
from apps.approval_engine.serializers import (
    ApprovalPolicySerializer,
    ApprovalRequestSerializer,
)
from apps.approval_engine.services import ApprovalEngine
from apps.service_desk.models import ApprovalRequest
from apps.service_desk.tenancy import get_active_company, require_company


class ApprovalPolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ApprovalPolicySerializer
    filterset_fields = ("entity_type", "is_active")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = ApprovalPolicy.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))

    @action(detail=False, methods=["post"])
    def bootstrap(self, request):
        company = require_company(request)
        policies = ApprovalEngine.ensure_default_policies(company)
        return Response(ApprovalPolicySerializer(policies, many=True).data)


class ApprovalInboxViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ApprovalRequestSerializer

    def get_queryset(self):
        return ApprovalEngine.pending_for(self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        approve(req, actor=request.user, note=request.data.get("note") or "")
        return Response(ApprovalRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        reject(req, actor=request.user, note=request.data.get("note") or "")
        return Response(ApprovalRequestSerializer(req).data)
