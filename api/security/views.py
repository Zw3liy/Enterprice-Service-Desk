from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mfa.services import MFAService
from security.sso import list_configured_providers


class SecurityStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "mfa_enabled": MFAService.is_enabled(request.user),
                "sso_providers": list_configured_providers(),
            }
        )
