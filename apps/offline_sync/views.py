from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.offline_sync.serializers import (
    OfflineMutationSerializer,
    SyncPullSerializer,
    SyncPushSerializer,
)
from apps.offline_sync.services import OfflineSyncService
from apps.service_desk.tenancy import require_company


class SyncPullAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SyncPullSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        payload = OfflineSyncService.pull(
            company,
            request.user,
            ser.validated_data["device_id"],
            since=ser.validated_data.get("since"),
        )
        return Response(payload)


class SyncPushAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SyncPushSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        results = OfflineSyncService.push(
            company,
            request.user,
            ser.validated_data["device_id"],
            ser.validated_data.get("mutations") or [],
        )
        return Response(
            OfflineMutationSerializer(results, many=True).data,
            status=status.HTTP_200_OK,
        )
