"""CMDB extensions on top of core Asset model."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Asset, Company, TimeStampedModel, UUIDPrimaryKeyModel


class CIClass(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="ci_classes")
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=60)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, blank=True, default="fa-server")

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ConfigurationItem(TimeStampedModel, UUIDPrimaryKeyModel):
    """Logical CI that may wrap or extend a physical Asset."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="configuration_items")
    asset = models.OneToOneField(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configuration_item",
    )
    ci_class = models.ForeignKey(
        CIClass, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    name = models.CharField(max_length=200)
    ci_id = models.CharField(max_length=80)
    environment = models.CharField(max_length=40, blank=True, default="production")
    criticality = models.PositiveSmallIntegerField(default=3)
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "ci_id")
        ordering = ["ci_id"]

    def __str__(self) -> str:
        return f"{self.ci_id} — {self.name}"


class CIRelationship(TimeStampedModel):
    class RelationType(models.TextChoices):
        DEPENDS_ON = "depends_on", "Depends on"
        RUNS_ON = "runs_on", "Runs on"
        CONNECTS_TO = "connects_to", "Connects to"
        HOSTED_ON = "hosted_on", "Hosted on"
        BACKS_UP = "backs_up", "Backs up"
        RELATED = "related", "Related"

    source = models.ForeignKey(
        ConfigurationItem, on_delete=models.CASCADE, related_name="outbound"
    )
    target = models.ForeignKey(
        ConfigurationItem, on_delete=models.CASCADE, related_name="inbound"
    )
    relation_type = models.CharField(
        max_length=30, choices=RelationType.choices, default=RelationType.RELATED
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("source", "target", "relation_type")

    def __str__(self) -> str:
        return f"{self.source_id} {self.relation_type} {self.target_id}"


class DiscoveryResult(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="discovery_results"
    )
    source = models.CharField(max_length=80, default="manual")
    hostname = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=32, blank=True)
    os_name = models.CharField(max_length=120, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    matched_ci = models.ForeignKey(
        ConfigurationItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discovery_hits",
    )
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]