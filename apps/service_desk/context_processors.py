"""Template context processors."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def service_desk_globals(request: HttpRequest) -> dict:
    unread = 0
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        try:
            from apps.service_desk.models import Notification

            unread = (
                Notification.objects.filter(
                    recipient=request.user,
                    status__in=[
                        Notification.Status.PENDING,
                        Notification.Status.SENT,
                    ],
                ).count()
            )
        except Exception:
            unread = 0

    return {
        "ESD_PRODUCT_NAME": "Enterprise Service Desk",
        "ESD_UNREAD_NOTIFICATIONS": unread,
        "ESD_DEBUG": settings.DEBUG,
    }
