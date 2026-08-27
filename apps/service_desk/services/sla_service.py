"""
SLA business service.

Everything that creates or advances an SLA clock lives here. Views,
signals and the scheduled command all call into this module; none of
them write to ``TicketSLA`` or ``SLAEscalation`` directly.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.service_desk.models import (
    SLAEscalation,
    SLAPolicy,
    Ticket,
    TicketHistory,
    TicketSLA,
)


class SLAService:
    """
    Attach, advance and evaluate ticket service levels.
    """

    # Statuses that stop the resolution clock.
    CLOSING_STATUSES = {"resolved", "awaiting_confirmation", "closed"}

    # Statuses where the ticket is waiting on somebody outside the
    # service desk, so escalating would be noise.
    PAUSED_STATUSES = {"pending"}

    # ==========================================================
    # Policy resolution
    # ==========================================================

    @staticmethod
    def resolve_policy(ticket: Ticket):
        """
        The policy that applies to this ticket.

        A policy scoped to the ticket's department always beats the
        organisation-wide default for the same priority. Returns None
        when nothing is configured — SLA tracking is opt-in, and a
        service desk with no policies must keep working.
        """

        queryset = SLAPolicy.objects.filter(
            priority=ticket.priority,
            is_active=True,
        )

        if ticket.department_id:
            specific = queryset.filter(
                department_id=ticket.department_id
            ).first()

            if specific:
                return specific

        return queryset.filter(department__isnull=True).first()

    # ==========================================================
    # Attachment
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def attach_to_ticket(ticket: Ticket, policy=None, now=None):
        """
        Start the clock for a ticket.

        Idempotent: a ticket that already has an SLA record keeps it,
        so re-running this (or creating a ticket through a path that
        already attached one) never resets a live deadline.
        """

        existing = TicketSLA.objects.filter(ticket=ticket).first()

        if existing:
            return existing

        policy = policy or SLAService.resolve_policy(ticket)

        if policy is None:
            return None

        now = now or timezone.now()

        return TicketSLA.objects.create(
            ticket=ticket,
            policy=policy,
            started_at=now,
            response_due_at=now + timedelta(minutes=policy.response_minutes),
            resolution_due_at=now
            + timedelta(minutes=policy.resolution_minutes),
        )

    @staticmethod
    @transaction.atomic
    def recalculate(ticket: Ticket, now=None):
        """
        Re-derive deadlines after a priority change.

        Only the *unmet* clocks move: a first response that already
        happened is history and is not re-judged.
        """

        record = TicketSLA.objects.filter(ticket=ticket).first()

        if record is None:
            return SLAService.attach_to_ticket(ticket, now=now)

        policy = SLAService.resolve_policy(ticket)

        if policy is None:
            return record

        record.policy = policy

        if record.first_responded_at is None:
            record.response_due_at = record.started_at + timedelta(
                minutes=policy.response_minutes
            )

        if record.resolved_at is None:
            record.resolution_due_at = record.started_at + timedelta(
                minutes=policy.resolution_minutes
            )

        record.save()

        return record

    # ==========================================================
    # Clock stops
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def mark_first_response(ticket: Ticket, now=None):
        """
        Stop the response clock the first time the service desk acts.
        """

        record = TicketSLA.objects.filter(ticket=ticket).first()

        if record is None or record.first_responded_at is not None:
            return record

        now = now or timezone.now()

        record.first_responded_at = now
        record.response_breached = now > record.response_due_at
        record.save(
            update_fields=[
                "first_responded_at",
                "response_breached",
                "updated_at",
            ]
        )

        return record

    @staticmethod
    @transaction.atomic
    def mark_resolved(ticket: Ticket, now=None):
        """
        Stop the resolution clock.
        """

        record = TicketSLA.objects.filter(ticket=ticket).first()

        if record is None or record.resolved_at is not None:
            return record

        now = now or timezone.now()

        record.resolved_at = now
        record.resolution_breached = now > record.resolution_due_at

        # Resolving without ever logging a response still counts as a
        # response at that moment — otherwise the response clock would
        # run forever on a ticket nobody can act on again.
        if record.first_responded_at is None:
            record.first_responded_at = now
            record.response_breached = now > record.response_due_at

        record.save()

        return record

    @staticmethod
    @transaction.atomic
    def reopen(ticket: Ticket, now=None):
        """
        Restart the resolution clock when a closed ticket is reopened.
        """

        record = TicketSLA.objects.filter(ticket=ticket).first()

        if record is None:
            return SLAService.attach_to_ticket(ticket, now=now)

        if record.resolved_at is None:
            return record

        now = now or timezone.now()
        policy = record.policy or SLAService.resolve_policy(ticket)

        record.resolved_at = None
        record.resolution_breached = False

        if policy:
            record.resolution_due_at = now + timedelta(
                minutes=policy.resolution_minutes
            )

        record.save()

        return record

    @staticmethod
    @transaction.atomic
    def set_paused(ticket: Ticket, paused: bool):
        record = TicketSLA.objects.filter(ticket=ticket).first()

        if record is None or record.paused == paused:
            return record

        record.paused = paused
        record.save(update_fields=["paused", "updated_at"])

        return record

    # ==========================================================
    # Status hook
    # ==========================================================

    @staticmethod
    def on_status_change(ticket: Ticket, from_status: str, to_status: str,
                         now=None):
        """
        Single entry point used by TicketService.change_status.
        """

        if to_status == "in_progress":
            SLAService.mark_first_response(ticket, now=now)

        if to_status in SLAService.CLOSING_STATUSES:
            SLAService.mark_resolved(ticket, now=now)

        if from_status == "closed" and to_status == "open":
            SLAService.reopen(ticket, now=now)

        SLAService.set_paused(
            ticket,
            to_status in SLAService.PAUSED_STATUSES,
        )

    # ==========================================================
    # Evaluation / escalation
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def evaluate(record: TicketSLA, now=None):
        """
        Raise any warning/breach escalations this clock has earned.

        Returns the escalations *created by this call* — already
        recorded ones are not returned again, which is what makes the
        scheduled command safe to run every minute.
        """

        now = now or timezone.now()

        created = []

        def raise_escalation(kind, detail):
            escalation, was_created = SLAEscalation.objects.get_or_create(
                ticket_sla=record,
                kind=kind,
                defaults={"detail": detail, "created_at": now},
            )

            if was_created:
                created.append(escalation)

        dirty = False

        # --- Response clock ---
        if record.first_responded_at is None:
            if now > record.response_due_at:
                if not record.response_breached:
                    record.response_breached = True
                    dirty = True

                raise_escalation(
                    SLAEscalation.KIND_RESPONSE_BREACH,
                    f"Response overdue since {record.response_due_at:%Y-%m-%d %H:%M}.",
                )

            elif now >= record.response_warning_at:
                raise_escalation(
                    SLAEscalation.KIND_RESPONSE_WARNING,
                    f"Response due {record.response_due_at:%Y-%m-%d %H:%M}.",
                )

        # --- Resolution clock ---
        if record.resolved_at is None:
            if now > record.resolution_due_at:
                if not record.resolution_breached:
                    record.resolution_breached = True
                    dirty = True

                raise_escalation(
                    SLAEscalation.KIND_RESOLUTION_BREACH,
                    f"Resolution overdue since {record.resolution_due_at:%Y-%m-%d %H:%M}.",
                )

            elif now >= record.resolution_warning_at:
                raise_escalation(
                    SLAEscalation.KIND_RESOLUTION_WARNING,
                    f"Resolution due {record.resolution_due_at:%Y-%m-%d %H:%M}.",
                )

        if dirty:
            record.save(
                update_fields=[
                    "response_breached",
                    "resolution_breached",
                    "updated_at",
                ]
            )

        for escalation in created:
            SLAService._record_history(record, escalation)
            SLAService._notify(record, escalation)

        return created

    @staticmethod
    def _record_history(record: TicketSLA, escalation: SLAEscalation):
        """
        Put the escalation on the ticket's own audit trail so it is
        visible where an engineer actually looks.
        """

        TicketHistory.record(
            ticket=record.ticket,
            event_type=TicketHistory.EVENT_UPDATED,
            user=None,
            comment=f"SLA {escalation.get_kind_display()}: {escalation.detail}",
            metadata={
                "sla_escalation_id": escalation.pk,
                "sla_escalation_kind": escalation.kind,
            },
        )

    @staticmethod
    def _notify(record: TicketSLA, escalation: SLAEscalation):
        """
        Hand the escalation to the notification boundary.

        Imported lazily and guarded so an SLA run can never be taken
        down by the notification layer.
        """

        try:
            from apps.service_desk.services.notification_service import (
                NotificationService,
            )
        except ImportError:  # pragma: no cover - notifications optional
            return

        NotificationService.notify_sla_escalation(record, escalation)

    @staticmethod
    def process_due(now=None, queryset=None):
        """
        Evaluate every live SLA clock.

        Used by the ``process_sla`` management command. Paused clocks
        (ticket pending on the requester) and fully-stopped clocks are
        skipped.
        """

        now = now or timezone.now()

        if queryset is None:
            queryset = TicketSLA.objects.all()

        queryset = (
            queryset.filter(paused=False)
            .select_related("ticket", "policy")
            .exclude(
                first_responded_at__isnull=False,
                resolved_at__isnull=False,
            )
        )

        created = []

        for record in queryset:
            created.extend(SLAService.evaluate(record, now=now))

        return created

    # ==========================================================
    # Policy administration
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_policy(**data):
        policy = SLAPolicy(**data)
        policy.full_clean()
        policy.save()
        return policy

    @staticmethod
    @transaction.atomic
    def update_policy(policy: SLAPolicy, **fields):
        for field, value in fields.items():
            if hasattr(policy, field):
                setattr(policy, field, value)

        policy.full_clean()
        policy.save()
        return policy

    @staticmethod
    def assert_policy_scope_allowed(user, department):
        """
        Only Administrators may write organisation-wide policies; a
        Manager is limited to the departments they manage.
        """

        from apps.service_desk.security.policies import is_administrator

        if user is None or is_administrator(user):
            return

        if department is None:
            raise ValidationError(
                "Only administrators can create organisation-wide "
                "SLA policies."
            )

        if not user.managed_departments.filter(pk=department.pk).exists():
            raise ValidationError(
                "You can only manage SLA policies for departments you "
                "manage."
            )
