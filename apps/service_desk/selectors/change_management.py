from django.db.models import Q

from apps.service_desk.models import ChangeRequest
from apps.service_desk.security.policies import (
    get_ticket_queryset,
)


def get_change_requests(user):
    visible_tickets = get_ticket_queryset(user)

    return (
        ChangeRequest.objects
        .filter(
            Q(ticket__in=visible_tickets)
            | Q(requester=user)
        )
        .select_related("ticket", "requester")
        .prefetch_related("cab_decisions", "tasks")
        .distinct()
    )