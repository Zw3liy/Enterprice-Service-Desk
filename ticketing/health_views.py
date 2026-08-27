from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def liveness(request):
    return JsonResponse({"status": "alive"})


@never_cache
@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()

        if not row or row[0] != 1:
            raise RuntimeError("Unexpected database health response")

        return JsonResponse({"status": "ready"})
    except Exception:
        return JsonResponse(
            {"status": "unavailable"},
            status=503,
        )
