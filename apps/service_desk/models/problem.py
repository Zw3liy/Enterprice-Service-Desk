from django.conf import settings
from django.db import models

from .department import Department
from .ticket import Ticket


class Problem(models.Model):
    """
    Enterprise Problem record.

    Represents the underlying cause behind one or more
    Incidents (Tickets), tracked through investigation to
    resolution per ITIL Problem Management.
    """

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("investigating", "Investigating"),
        ("known_error", "Known Error"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        db_index=True,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="created_problems",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_problems",
    )

    root_cause = models.TextField(
        blank=True,
        default="",
    )

    workaround = models.TextField(
        blank=True,
        default="",
    )

    is_known_error = models.BooleanField(
        default=False,
    )

    related_tickets = models.ManyToManyField(
        Ticket,
        blank=True,
        related_name="problems",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Problem"
        verbose_name_plural = "Problems"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["department"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"[{self.pk}] {self.title}"
