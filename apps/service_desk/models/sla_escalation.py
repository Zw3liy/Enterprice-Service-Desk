from django.db import models

from .ticket import Ticket


class SLAEscalation(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="sla_escalations",
    )

    escalated_at = models.DateTimeField(
        auto_now_add=True,
    )

    breach_timestamp = models.DateTimeField()

    class Meta:
        unique_together = (
            "ticket",
            "breach_timestamp",
        )

        indexes = [
            models.Index(
                fields=[
                    "ticket",
                    "breach_timestamp",
                ],
                name="service_des_ticket__585168_idx",
            )
        ]

    def __str__(self):
        return f"SLA escalation for {self.ticket}"
