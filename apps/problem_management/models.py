"""ITIL Problem Management domain models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, KnowledgeArticle, Ticket, TimeStampedModel


class ProblemRecord(TimeStampedModel):
    class State(models.TextChoices):
        NEW = "new", "New"
        ROOT_CAUSE = "root_cause", "Root cause analysis"
        KNOWN_ERROR = "known_error", "Known error"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    ticket = models.OneToOneField(
        Ticket, on_delete=models.CASCADE, related_name="problem_record"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="problems"
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.NEW)
    root_cause = models.TextField(blank=True)
    workaround = models.TextField(blank=True)
    known_error_article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="known_errors",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_problems",
    )
    related_incidents = models.ManyToManyField(
        Ticket, blank=True, related_name="related_problems"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PRB-{self.ticket.ticket_number}"