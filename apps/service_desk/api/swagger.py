from django.http import JsonResponse

from apps.service_desk.api.openapi import OPENAPI


def openapi_json(request):
    return JsonResponse(OPENAPI)
