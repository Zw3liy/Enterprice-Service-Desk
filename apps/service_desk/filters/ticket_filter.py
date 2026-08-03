import django_filters

from apps.service_desk.models import Ticket


class TicketFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_q")
    open_only = django_filters.BooleanFilter(method="filter_open")

    class Meta:
        model = Ticket
        fields = ["status", "priority", "queue", "assignee", "ticket_type", "company"]

    def filter_q(self, qs, name, value):
        from django.db.models import Q

        if not value:
            return qs
        return qs.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(ticket_number__icontains=value)
        )

    def filter_open(self, qs, name, value):
        if value:
            return qs.filter(closed_at__isnull=True, status__is_terminal=False)
        return qs
