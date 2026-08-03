from django.http import HttpResponse
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from apps.service_desk.tenancy import get_active_company
from security.siem.export import recent_export


class SIEMExportAPI(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        fmt = request.query_params.get("format", "json")
        if fmt not in {"json", "cef"}:
            fmt = "json"
        company = get_active_company(request)
        body = recent_export(company=company, limit=int(request.query_params.get("limit") or 500), fmt=fmt)
        content_type = "application/json" if fmt == "json" else "text/plain"
        return HttpResponse(body, content_type=content_type)
