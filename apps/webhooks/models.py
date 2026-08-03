"""Webhook delivery log (endpoints live on service_desk.WebhookEndpoint)."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel, WebhookEndpoint


class WebhookDelivery(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="webhook_deliveries"
    )
    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    attempt = models.PositiveSmallIntegerField(default=1)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "webhook deliveries"

    def __str__(self) -> str:
        return f"{self.event} → {self.endpoint_id} ({self.status})"