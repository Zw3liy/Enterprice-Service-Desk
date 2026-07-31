"""DRF exception handling."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        payload = {
            "success": False,
            "errors": response.data,
            "status_code": response.status_code,
        }
        response.data = payload
        return response

    logger.exception("unhandled api exception")
    return Response(
        {
            "success": False,
            "errors": {"detail": "Internal server error"},
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
