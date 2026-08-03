"""Network discovery scan jobs and host inventory."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class DiscoveryScan(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="discovery_scans"
    )
    name = models.CharField(max_length=160)
    cidr = models.CharField(max_length=64, help_text="e.g. 10.0.0.0/24")
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    hosts_found = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.cidr})"


class DiscoveredHost(TimeStampedModel):
    scan = models.ForeignKey(
        DiscoveryScan, on_delete=models.CASCADE, related_name="hosts"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="discovered_hosts"
    )
    ip_address = models.GenericIPAddressField()
    hostname = models.CharField(max_length=200, blank=True)
    mac_address = models.CharField(max_length=32, blank=True)
    open_ports = models.JSONField(default=list, blank=True)
    os_guess = models.CharField(max_length=120, blank=True)
    is_alive = models.BooleanField(default=True)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["ip_address"]
        unique_together = ("scan", "ip_address")

    def __str__(self) -> str:
        return self.hostname or self.ip_address
