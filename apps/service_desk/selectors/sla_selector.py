"""
Read-only SLA query layer.

Every public method takes an already RBAC-scoped queryset (or derives
from one) rather than a user, so no selector here can widen what the
caller is allowed to see.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.service_desk.models import SLAEscalation, SLAPolicy, TicketSLA


class SLASelector:

    # ------------------------------------------------------------------
    # Policies
    # ------------------------------------------------------------------

    @staticmethod
    def policies_for_user(user) -> QuerySet[SLAPolicy]:
        """
        Policy visibility.

        Administrator: every policy.
        Manager: policies for their departments plus the global
                 defaults those departments inherit.
        Everyone else: none.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None or not user.is_authenticated:
            return SLAPolicy.objects.none()

        if is_administrator(user):
            return SLAPolicy.objects.select_related("department").all()

        if is_manager(user):
            return SLAPolicy.objects.select_related("department").filter(
                Q(department__in=user.managed_departments.all())
                | Q(department__isnull=True)
            )

        return SLAPolicy.objects.none()

    # ------------------------------------------------------------------
    # Ticket clocks
    # ------------------------------------------------------------------

    @staticmethod
    def for_tickets(ticket_queryset) -> QuerySet[TicketSLA]:
        return (
            TicketSLA.objects.filter(ticket__in=ticket_queryset)
            .select_related("ticket", "policy", "ticket__assigned_to")
        )

    @staticmethod
    def breached(ticket_queryset) -> QuerySet[TicketSLA]:
        return SLASelector.for_tickets(ticket_queryset).filter(
            Q(response_breached=True) | Q(resolution_breached=True)
        )

    @staticmethod
    def at_risk(ticket_queryset, now=None) -> list[TicketSLA]:
        """
        Clocks inside their warning window but not yet breached.

        The warning point depends on each record's own threshold, so
        this is evaluated in Python over the (already scoped, already
        narrowed) open set rather than pushed into SQL.
        """

        now = now or timezone.now()

        candidates = (
            SLASelector.for_tickets(ticket_queryset)
            .filter(response_breached=False, resolution_breached=False)
            .filter(Q(resolved_at__isnull=True) | Q(first_responded_at__isnull=True))
        )

        return [
            record
            for record in candidates
            if record.overall_state(now) == TicketSLA.STATE_AT_RISK
        ]

    @staticmethod
    def dashboard_summary(ticket_queryset, now=None) -> dict:
        """
        Counts for the dashboard SLA card, scoped to the caller's own
        ticket queryset.
        """

        now = now or timezone.now()

        records = SLASelector.for_tickets(ticket_queryset)

        tracked = records.count()
        breached = SLASelector.breached(ticket_queryset).count()
        at_risk = len(SLASelector.at_risk(ticket_queryset, now=now))

        return {
            "tracked": tracked,
            "breached": breached,
            "at_risk": at_risk,
            "on_track": max(tracked - breached - at_risk, 0),
            "untracked": ticket_queryset.filter(sla__isnull=True).count(),
        }

    # ------------------------------------------------------------------
    # Escalations
    # ------------------------------------------------------------------

    @staticmethod
    def escalations(ticket_queryset, limit: int = 25):
        return (
            SLAEscalation.objects.filter(
                ticket_sla__ticket__in=ticket_queryset
            )
            .select_related("ticket_sla", "ticket_sla__ticket")
            .order_by("-created_at")[:limit]
        )
