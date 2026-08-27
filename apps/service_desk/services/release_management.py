from apps.service_desk.models import Release
from apps.service_desk.models.ticket_history import TicketHistory
from apps.service_desk.security.policies import (
    get_ticket_queryset,
    is_administrator,
    is_manager,
)


def _can_manage_release(user, release):
    if is_administrator(user) or is_manager(user):
        return release.change_request.ticket in get_ticket_queryset(user)
    return False


def schedule_release(*, release, user):
    if not _can_manage_release(user, release):
        raise PermissionError("User is not authorized to schedule this release.")

    if release.change_request.status != "approved":
        raise ValueError("Only approved Change Requests may be scheduled.")

    old_status = release.status
    release.status = Release.Status.PLANNED
    release.save(update_fields=["status", "updated_at"])

    TicketHistory.record(
        ticket=release.change_request.ticket,
        event_type=TicketHistory.EVENT_UPDATED,
        user=user,
        old_value=old_status,
        new_value=release.status,
        metadata={"release_id": release.pk, "action": "schedule_release"},
    )

    return release


def execute_deployment(*, release, user):
    if not _can_manage_release(user, release):
        raise PermissionError("User is not authorized to execute this release.")

    old_status = release.status
    release.status = Release.Status.IN_PROGRESS
    release.save(update_fields=["status", "updated_at"])

    TicketHistory.record(
        ticket=release.change_request.ticket,
        event_type=TicketHistory.EVENT_UPDATED,
        user=user,
        old_value=old_status,
        new_value=release.status,
        metadata={"release_id": release.pk, "action": "execute_deployment"},
    )

    return release


def rollback_release(*, release, user):
    if not _can_manage_release(user, release):
        raise PermissionError("User is not authorized to roll back this release.")

    old_status = release.status
    release.status = Release.Status.ROLLED_BACK
    release.save(update_fields=["status", "updated_at"])

    TicketHistory.record(
        ticket=release.change_request.ticket,
        event_type=TicketHistory.EVENT_UPDATED,
        user=user,
        old_value=old_status,
        new_value=release.status,
        metadata={"release_id": release.pk, "action": "rollback_release"},
    )

    return release