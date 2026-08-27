from django.db import models

from .change_management import ChangeRequest


class Release(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        DEPLOYED = "deployed", "Deployed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    change_request = models.ForeignKey(
        ChangeRequest,
        on_delete=models.CASCADE,
        related_name="releases",
    )
    version_number = models.CharField(max_length=100)
    scheduled_deployment_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    release_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_deployment_time"]

    def __str__(self):
        return f"{self.version_number} - {self.get_status_display()}"


class ReleaseItem(models.Model):
    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=255)
    component = models.CharField(max_length=255, blank=True, default="")
    artifact = models.CharField(max_length=255, blank=True, default="")
    deployed = models.BooleanField(default=False)

    def __str__(self):
        return self.name