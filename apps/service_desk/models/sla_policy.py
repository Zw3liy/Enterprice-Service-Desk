from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models


class SLAPolicy(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    duration_minutes = models.PositiveIntegerField(
        default=60,
    )

    description = models.TextField(
        blank=True,
    )

    def duration(self):
        """Return the configured SLA duration as a timedelta."""
        return timedelta(minutes=self.duration_minutes)

    def clean(self):
        super().clean()

        if self.duration_minutes <= 0:
            raise ValidationError(
                {
                    "duration_minutes": (
                        "Duration minutes must be a positive integer "
                        "greater than zero."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
