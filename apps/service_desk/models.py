from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Ticket(models.Model):

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("ON_HOLD", "On Hold"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]

    CATEGORY_CHOICES = [
        ("INCIDENT", "Incident"),
        ("SERVICE_REQUEST", "Service Request"),
        ("PROBLEM", "Problem"),
        ("CHANGE", "Change"),
    ]

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )

    subject = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="INCIDENT",
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_tickets",
        on_delete=models.CASCADE,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tickets",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):

        if not self.ticket_number:

            year = timezone.now().year

            last = (
                Ticket.objects
                .filter(ticket_number__startswith=f"INC-{year}")
                .count()
            )

            self.ticket_number = (
                f"INC-{year}-{last + 1:05d}"
            )

        super().save(*args, **kwargs)

    def get_absolute_url(self):

        return reverse(
            "ticket_detail",
            kwargs={"pk": self.pk},
        )