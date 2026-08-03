from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.multi_tenant.billing import attach_default_plan
from apps.multi_tenant.models import TenantDomain, TenantSettings
from apps.multi_tenant.serializers import (
    CompanyTenantSerializer,
    TenantDomainSerializer,
    TenantProvisionSerializer,
    TenantSettingsSerializer,
)
from apps.multi_tenant.services import TenantService
from apps.service_desk.models import Company
from apps.service_desk.tenancy import get_active_company, require_company


class TenantListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            qs = Company.objects.filter(is_active=True).order_by("name")
        else:
            company = get_active_company(request)
            qs = Company.objects.filter(pk=company.pk) if company else Company.objects.none()
        return Response(CompanyTenantSerializer(qs, many=True).data)


class TenantProvisionAPI(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        ser = TenantProvisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        company = TenantService.provision(
            name=data["name"],
            slug=data.get("slug") or None,
            admin_email=data.get("admin_email") or "",
            domain=data.get("domain") or "",
        )
        try:
            attach_default_plan(company, plan_code=data.get("plan_code") or "starter")
        except Exception:
            pass
        return Response(CompanyTenantSerializer(company).data, status=status.HTTP_201_CREATED)


class TenantSettingsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = require_company(request)
        settings_obj, _ = TenantSettings.objects.get_or_create(company=company)
        return Response(TenantSettingsSerializer(settings_obj).data)

    def patch(self, request):
        company = require_company(request)
        if not request.user.is_staff:
            return Response({"detail": "Staff only"}, status=403)
        settings_obj, _ = TenantSettings.objects.get_or_create(company=company)
        ser = TenantSettingsSerializer(settings_obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class TenantDomainViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = TenantDomainSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = TenantDomain.objects.select_related("company")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))
