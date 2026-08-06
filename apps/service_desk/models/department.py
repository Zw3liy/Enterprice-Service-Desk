from django.conf import settings
from django.db import models


class Department(models.Model):
    """
    Enterprise organizational unit.

    Managers assigned here can view/manage
    tickets belonging to this department.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="managed_departments",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name