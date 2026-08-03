from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.document_indexing.serializers import SearchQuerySerializer
from apps.document_indexing.services import DocumentIndexService
from apps.service_desk.tenancy import require_company


class DocumentSearchAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = SearchQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        results = DocumentIndexService.search(
            company,
            ser.validated_data["q"],
            limit=ser.validated_data.get("limit") or 25,
        )
        return Response({"results": results, "count": len(results)})


class DocumentReindexAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Staff only"}, status=403)
        company = require_company(request)
        stats = DocumentIndexService.reindex_company(company)
        return Response(stats, status=status.HTTP_200_OK)
