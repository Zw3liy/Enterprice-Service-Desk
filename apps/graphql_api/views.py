import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.graphql_api.schema import execute_query
from apps.service_desk.tenancy import get_active_company


class GraphQLAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if isinstance(request.data, dict):
            body = request.data
        else:
            try:
                body = json.loads(request.body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                body = {}
        query = body.get("query") or ""
        variables = body.get("variables") or {}
        result = execute_query(
            query,
            variables,
            user=request.user,
            company=get_active_company(request),
        )
        status_code = 200 if "errors" not in result else 400
        return JsonResponse(result, status=status_code)

    def get(self, request):
        return JsonResponse(
            {
                "graphql": True,
                "endpoint": "/graphql/",
                "examples": [
                    '{ tickets { id ticketNumber title } }',
                    '{ dashboard { openTickets totalTickets } }',
                    '{ ticket(id: 1) { id title status } }',
                ],
            }
        )


@csrf_exempt
def graphql_http(request):
    """Function-based alias for non-DRF clients."""
    view = GraphQLAPI.as_view()
    return view(request)
