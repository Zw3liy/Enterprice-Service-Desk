from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.tenant.serializers import TenantProvisionSerializer, TenantSerializer
from apps.multi_tenant.services import TenantService
from apps.service_desk.models import Company


class TenantListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Company.objects.filter(is_active=True).order_by("name")
        if not request.user.is_staff:
            # non-staff see only session company if set
            company_id = request.session.get("company_id")
            qs = qs.filter(pk=company_id) if company_id else qs.none()
        return Response(TenantSerializer(qs, many=True).data)


class TenantProvisionAPI(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        ser = TenantProvisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = TenantService.provision(
            name=ser.validated_data["name"],
            slug=ser.validated_data.get("slug") or None,
            admin_email=ser.validated_data.get("admin_email") or "",
        )
        return Response(TenantSerializer(company).data, status=status.HTTP_201_CREATED)
