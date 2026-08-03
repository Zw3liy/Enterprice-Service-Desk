"""Search index documents and terms."""

from __future__ import annotations

from django.db import models

from apps.service_desk.models import Company, TimeStampedModel


class IndexedDocument(TimeStampedModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="indexed_documents"
    )
    source_type = models.CharField(max_length=60)
    source_id = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    tokens = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "source_type", "source_id")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "source_type"]),
        ]

    def __str__(self) -> str:
        return self.title
