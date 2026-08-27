"""
Read-only notification query layer.

Every method is keyed on the owning user; there is no path here that
returns another person's notifications.
"""

from __future__ import annotations

from django.db.models import QuerySet

from apps.service_desk.models import Notification


class NotificationSelector:

    @staticmethod
    def for_user(user) -> QuerySet[Notification]:
        if user is None or not user.is_authenticated:
            return Notification.objects.none()

        return Notification.objects.filter(
            recipient=user
        ).select_related("ticket", "problem")

    @staticmethod
    def unread(user) -> QuerySet[Notification]:
        return NotificationSelector.for_user(user).filter(
            read_at__isnull=True
        )

    @staticmethod
    def unread_count(user) -> int:
        return NotificationSelector.unread(user).count()

    @staticmethod
    def recent(user, limit: int = 10):
        return NotificationSelector.for_user(user)[:limit]
