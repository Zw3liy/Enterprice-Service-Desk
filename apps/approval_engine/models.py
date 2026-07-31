"""Generic approval definitions (ticket approvals remain on service_desk)."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import ApprovalRequest, Company, TimeStampedModel

__all__ = ["ApprovalRequest", "ApprovalPolicy"]


class ApprovalPolicy(TimeStampedModel):
    """Policy describing when approvals are required."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="approval_policies"
    )
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=60)
    entity_type = models.CharField(
        max_length=40,
        default="ticket",
        help_text="ticket | change | purchase_request",
    )
    conditions = models.JSONField(default=dict, blank=True)
    min_approvers = models.PositiveSmallIntegerField(default=1)
    approver_role = models.CharField(max_length=60, blank=True, default="approver")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]
        verbose_name_plural = "approval policies"

    def __str__(self) -> str:
        return self.name
