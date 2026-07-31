"""Async notification delivery hooks."""

import logging

logger = logging.getLogger(__name__)


def deliver_pending_notifications(limit: int = 100) -> int:
    from django.utils import timezone

    from apps.service_desk.models import Notification
    from apps.service_desk.services.notification_service import NotificationService

    qs = Notification.objects.filter(status=Notification.Status.PENDING)[:limit]
    count = 0
    for note in qs:
        NotificationService._deliver_email(note)
        count += 1
    logger.info("delivered_pending=%s", count)
    return count
