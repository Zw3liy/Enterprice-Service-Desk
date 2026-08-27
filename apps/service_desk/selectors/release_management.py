from apps.service_desk.models import Release
from apps.service_desk.security.policies import get_ticket_queryset


def get_releases(user):
    visible_tickets = get_ticket_queryset(user)

    return Release.objects.filter(
        change_request__ticket__in=visible_tickets
    ).select_related(
        "change_request",
        "change_request__ticket",
    ).prefetch_related("items")