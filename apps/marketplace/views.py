from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.marketplace.models import InstalledApp, MarketplaceApp
from apps.marketplace.serializers import (
    InstallAppSerializer,
    InstalledAppSerializer,
    MarketplaceAppSerializer,
)
from apps.marketplace.services import MarketplaceService
from apps.service_desk.tenancy import get_active_company, require_company


class MarketplaceCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MarketplaceAppSerializer
    lookup_field = "slug"
    search_fields = ("name", "vendor", "short_description")
    filterset_fields = ("category", "is_premium")

    def get_queryset(self):
        MarketplaceService.seed_catalog()
        return MarketplaceApp.objects.filter(is_published=True)


class InstalledAppViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InstalledAppSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = InstalledApp.objects.select_related("app", "installed_by")
        if company:
            qs = qs.filter(company=company)
        return qs

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        install = self.get_object()
        MarketplaceService.disable(install, user=request.user)
        return Response(InstalledAppSerializer(install).data)


class MarketplaceInstallAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = InstallAppSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        try:
            install = MarketplaceService.install(
                company,
                ser.validated_data["app_slug"],
                config=ser.validated_data.get("config") or {},
                user=request.user,
            )
        except MarketplaceApp.DoesNotExist:
            return Response({"detail": "App not found"}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            InstalledAppSerializer(install).data, status=status.HTTP_201_CREATED
        )
