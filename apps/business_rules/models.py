"""Declarative business rules stored per tenant."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class BusinessRule(TimeStampedModel):
    class Scope(models.TextChoices):
        TICKET = "ticket", "Ticket"
        CHANGE = "change", "Change"
        ASSET = "asset", "Asset"
        GLOBAL = "global", "Global"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="business_rules"
    )
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=60)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.TICKET)
    description = models.TextField(blank=True)
    conditions = models.JSONField(default=dict, blank=True)
    actions = models.JSONField(default=list, blank=True)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    stop_on_match = models.BooleanField(default=False)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["priority", "name"]

    def __str__(self) -> str:
        return self.name
