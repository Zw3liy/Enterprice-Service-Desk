from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.pam.models import AccessRequest, PrivilegedAccount, PrivilegedSession
from apps.pam.serializers import (
    AccessRequestCreateSerializer,
    AccessRequestSerializer,
    PrivilegedAccountSerializer,
    PrivilegedSessionSerializer,
)
from apps.pam.services import PAMService
from apps.service_desk.middleware import get_client_ip
from apps.service_desk.tenancy import get_active_company, require_company

User = get_user_model()


class PrivilegedAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PrivilegedAccountSerializer
    search_fields = ("name", "system", "username")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = PrivilegedAccount.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))


class AccessRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AccessRequestSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = AccessRequest.objects.select_related("account", "requester", "approver")
        if company:
            qs = qs.filter(company=company)
        if not self.request.user.is_staff:
            qs = qs.filter(requester=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        ser = AccessRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        account = get_object_or_404(
            PrivilegedAccount, pk=ser.validated_data["account_id"], company=company
        )
        approver = None
        if ser.validated_data.get("approver_id"):
            approver = get_object_or_404(User, pk=ser.validated_data["approver_id"])
        req = PAMService.request_access(
            account,
            request.user,
            justification=ser.validated_data["justification"],
            minutes=ser.validated_data.get("requested_minutes") or 60,
            approver=approver,
        )
        return Response(AccessRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Staff only"}, status=403)
        req = self.get_object()
        approved = bool(request.data.get("approved"))
        PAMService.decide(
            req,
            approved=approved,
            actor=request.user,
            note=request.data.get("note") or "",
        )
        return Response(AccessRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def start_session(self, request, pk=None):
        req = self.get_object()
        if req.requester_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Forbidden"}, status=403)
        try:
            session = PAMService.start_session(
                req, client_ip=get_client_ip(request)
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            PrivilegedSessionSerializer(session).data, status=status.HTTP_201_CREATED
        )


class PrivilegedSessionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PrivilegedSessionSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = PrivilegedSession.objects.select_related("access_request__account")
        if company:
            qs = qs.filter(access_request__company=company)
        if not self.request.user.is_staff:
            qs = qs.filter(access_request__requester=self.request.user)
        return qs

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        session = self.get_object()
        PAMService.end_session(session, note=request.data.get("note") or "")
        return Response(PrivilegedSessionSerializer(session).data)
