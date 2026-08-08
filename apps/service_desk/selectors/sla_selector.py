from django.db import models
from django.utils.timezone import now
from apps.service_desk.models import Ticket

class SLASelector:

    @staticmethod
    def get_tickets_breached_sla(user):
        """ Return tickets where SLA is breached accessible by the given user. """
        from apps.service_desk.security.policies import get_ticket_queryset
        queryset = get_ticket_queryset(user)
        now_time = now()
        return queryset.filter(sla_policy__isnull=False).annotate(
            deadline=models.ExpressionWrapper(
                models.F('created_at') + models.F('sla_policy__duration_minutes') * 60,
                output_field=models.DateTimeField()
            )
        ).filter(deadline__lt=now_time)
