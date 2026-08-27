"""
Service Level Agreement models.

Design notes
------------
This is the *only* SLA architecture in the repository. The
``apps/service_desk/sla/`` package that ships alongside it is empty
scaffolding (every file is 0 bytes) and is not an installed app; these
models live in ``apps.service_desk.models`` with every other live
model, matching ADR-009's "extend the one real app" decision rather
than standing up a competing second implementation.

Three records:

``SLAPolicy``
    The rule: for this priority (optionally narrowed to one
    department), a first response is owed within N minutes and a
    resolution within M minutes.

``TicketSLA``
    The clock attached to one ticket, holding the concrete deadlines
    computed when the ticket was raised plus the timestamps that stop
    each clock. Deadlines are frozen at attach time on purpose — if a
    policy is edited later, tickets already under way keep the terms
    they were raised under.

``SLAEscalation``
    An immutable record that a warning or a breach happened. Unique
    per (ticket SLA, kind) so the scheduled processor is idempotent
    and can be run as often as the operator likes.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .department import Department
from .ticket import Ticket


class SLAPolicy(models.Model):
    """
    Priority-based (optionally department-specific) service targets.
    """

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Ticket.PRIORITY_CHOICES,
        db_index=True,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sla_policies",
        help_text=(
            "Leave empty for the organisation-wide default for this "
            "priority. A department-specific policy always wins over "
            "the default."
        ),
    )

    response_minutes = models.PositiveIntegerField(
        help_text="Minutes allowed for the first response.",
    )

    resolution_minutes = models.PositiveIntegerField(
        help_text="Minutes allowed to resolve the ticket.",
    )

    warning_threshold_percent = models.PositiveSmallIntegerField(
        default=80,
        help_text=(
            "Percentage of the allowance at which the ticket is "
            "flagged as at risk (1-99)."
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "name"]
        verbose_name = "SLA Policy"
        verbose_name_plural = "SLA Policies"
        constraints = [
            models.UniqueConstraint(
                fields=["priority", "department"],
                name="unique_sla_policy_per_priority_department",
            ),
        ]
        indexes = [
            models.Index(fields=["priority", "department"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        scope = self.department.name if self.department else "Global"
        return f"{self.name} ({self.get_priority_display()} / {scope})"

    def clean(self):
        super().clean()

        errors = {}

        if self.response_minutes is not None and self.response_minutes < 1:
            errors["response_minutes"] = (
                "Response allowance must be at least one minute."
            )

        if (
            self.resolution_minutes is not None
            and self.response_minutes is not None
            and self.resolution_minutes < self.response_minutes
        ):
            errors["resolution_minutes"] = (
                "Resolution allowance cannot be shorter than the "
                "response allowance."
            )

        if self.warning_threshold_percent is not None and not (
            1 <= self.warning_threshold_percent <= 99
        ):
            errors["warning_threshold_percent"] = (
                "Warning threshold must be between 1 and 99 percent."
            )

        if errors:
            raise ValidationError(errors)


class TicketSLA(models.Model):
    """
    The live SLA clock for a single ticket.
    """

    STATE_MET = "met"
    STATE_ON_TRACK = "on_track"
    STATE_AT_RISK = "at_risk"
    STATE_BREACHED = "breached"

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name="sla",
    )

    policy = models.ForeignKey(
        SLAPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_slas",
    )

    started_at = models.DateTimeField(
        default=timezone.now,
    )

    response_due_at = models.DateTimeField()

    resolution_due_at = models.DateTimeField()

    first_responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    response_breached = models.BooleanField(
        default=False,
        db_index=True,
    )

    resolution_breached = models.BooleanField(
        default=False,
        db_index=True,
    )

    paused = models.BooleanField(
        default=False,
        help_text=(
            "Set while the ticket is pending on the requester; the "
            "clock keeps its deadlines but is excluded from "
            "escalation processing."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resolution_due_at"]
        verbose_name = "Ticket SLA"
        verbose_name_plural = "Ticket SLAs"
        indexes = [
            models.Index(fields=["response_due_at"]),
            models.Index(fields=["resolution_due_at"]),
            models.Index(fields=["response_breached"]),
            models.Index(fields=["resolution_breached"]),
        ]

    def __str__(self):
        return f"SLA for {self.ticket}"

    # ------------------------------------------------------------------
    # Derived state
    # ------------------------------------------------------------------

    def warning_at(self, due_at):
        """
        The moment this deadline should start warning.

        Computed from the frozen ``started_at`` so a policy edit does
        not retroactively move a live ticket's warning point.
        """

        threshold = 80

        if self.policy and self.policy.warning_threshold_percent:
            threshold = self.policy.warning_threshold_percent

        allowance = due_at - self.started_at

        return self.started_at + (allowance * threshold) / 100

    @property
    def response_warning_at(self):
        return self.warning_at(self.response_due_at)

    @property
    def resolution_warning_at(self):
        return self.warning_at(self.resolution_due_at)

    def response_state(self, now=None):
        now = now or timezone.now()

        if self.first_responded_at:
            return (
                self.STATE_BREACHED
                if self.first_responded_at > self.response_due_at
                else self.STATE_MET
            )

        if now > self.response_due_at:
            return self.STATE_BREACHED

        if now >= self.response_warning_at:
            return self.STATE_AT_RISK

        return self.STATE_ON_TRACK

    def resolution_state(self, now=None):
        now = now or timezone.now()

        if self.resolved_at:
            return (
                self.STATE_BREACHED
                if self.resolved_at > self.resolution_due_at
                else self.STATE_MET
            )

        if now > self.resolution_due_at:
            return self.STATE_BREACHED

        if now >= self.resolution_warning_at:
            return self.STATE_AT_RISK

        return self.STATE_ON_TRACK

    def overall_state(self, now=None):
        """
        Worst of the two clocks — what the dashboard badge shows.
        """

        now = now or timezone.now()

        states = {self.response_state(now), self.resolution_state(now)}

        for state in (
            self.STATE_BREACHED,
            self.STATE_AT_RISK,
            self.STATE_ON_TRACK,
        ):
            if state in states:
                return state

        return self.STATE_MET

    @property
    def is_breached(self):
        return self.response_breached or self.resolution_breached


class SLAEscalation(models.Model):
    """
    Immutable record of an SLA warning or breach.
    """

    KIND_RESPONSE_WARNING = "response_warning"
    KIND_RESPONSE_BREACH = "response_breach"
    KIND_RESOLUTION_WARNING = "resolution_warning"
    KIND_RESOLUTION_BREACH = "resolution_breach"

    KIND_CHOICES = [
        (KIND_RESPONSE_WARNING, "Response Warning"),
        (KIND_RESPONSE_BREACH, "Response Breach"),
        (KIND_RESOLUTION_WARNING, "Resolution Warning"),
        (KIND_RESOLUTION_BREACH, "Resolution Breach"),
    ]

    BREACH_KINDS = {KIND_RESPONSE_BREACH, KIND_RESOLUTION_BREACH}

    ticket_sla = models.ForeignKey(
        TicketSLA,
        on_delete=models.CASCADE,
        related_name="escalations",
    )

    kind = models.CharField(
        max_length=32,
        choices=KIND_CHOICES,
        db_index=True,
    )

    detail = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SLA Escalation"
        verbose_name_plural = "SLA Escalations"
        constraints = [
            models.UniqueConstraint(
                fields=["ticket_sla", "kind"],
                name="unique_sla_escalation_per_kind",
            ),
        ]
        indexes = [
            models.Index(fields=["ticket_sla", "kind"]),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.ticket_sla.ticket}"

    @property
    def is_breach(self):
        return self.kind in self.BREACH_KINDS
