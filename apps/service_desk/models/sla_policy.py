from django.db import models
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError

class SLAPolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # Duration in minutes as integer (can be converted to timedelta)
    duration_minutes = models.PositiveIntegerField(default=60)
    description = models.TextField(blank=True)

    def duration(self):
        return timedelta(minutes=self.duration_minutes)

    def clean(self):
        if self.duration_minutes <= 0:
            raise ValidationError({'duration_minutes': 'Duration minutes must be a positive integer greater than zero.'})

    def save(self, *args, **kwargs):
        self.full_clean()  # Calls clean() and validates model
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
