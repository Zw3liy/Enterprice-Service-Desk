from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mfa.models import MFADevice
from apps.mfa.serializers import (
    MFAConfirmSerializer,
    MFADeviceSerializer,
    MFAEnrollSerializer,
    MFAVerifySerializer,
)
from apps.mfa.services import MFAService


@login_required
@require_http_methods(["GET", "POST"])
def mfa_setup(request):
    devices = MFADevice.objects.filter(user=request.user)
    pending = None
    backup_codes = request.session.pop("mfa_backup_codes", None)
    if request.method == "POST" and request.POST.get("action") == "enroll":
        pending = MFAService.enroll(request.user, name=request.POST.get("name") or "Authenticator")
    elif request.method == "POST" and request.POST.get("action") == "confirm":
        device = get_object_or_404(MFADevice, pk=request.POST.get("device_id"), user=request.user)
        if MFAService.confirm(device, request.POST.get("token") or ""):
            codes = MFAService.generate_backup_codes(request.user)
            request.session["mfa_backup_codes"] = codes
            messages.success(request, "MFA enabled.")
            return redirect("mfa:setup")
        messages.error(request, "Invalid token.")
        pending = device
    return render(
        request,
        "security/mfa_setup.html",
        {
            "title": "Multi-factor authentication",
            "devices": devices,
            "pending": pending,
            "backup_codes": backup_codes,
            "enabled": MFAService.is_enabled(request.user),
        },
    )


@login_required
@require_POST
def mfa_disable(request):
    MFAService.disable(request.user)
    messages.info(request, "MFA disabled.")
    return redirect("mfa:setup")


class MFAStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = MFADevice.objects.filter(user=request.user)
        return Response(
            {
                "enabled": MFAService.is_enabled(request.user),
                "devices": MFADeviceSerializer(devices, many=True).data,
            }
        )


class MFAEnrollAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = MFAEnrollSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        device = MFAService.enroll(request.user, name=ser.validated_data.get("name") or "Authenticator")
        data = MFADeviceSerializer(device).data
        data["secret"] = device.secret
        return Response(data, status=status.HTTP_201_CREATED)


class MFAConfirmAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = MFAConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        device = get_object_or_404(
            MFADevice, pk=ser.validated_data["device_id"], user=request.user
        )
        ok = MFAService.confirm(device, ser.validated_data["token"])
        if not ok:
            return Response({"detail": "Invalid token"}, status=400)
        codes = MFAService.generate_backup_codes(request.user)
        return Response({"confirmed": True, "backup_codes": codes})


class MFAVerifyAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = MFAVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ok = MFAService.verify_user(request.user, ser.validated_data["token"])
        return Response({"valid": ok}, status=200 if ok else 400)