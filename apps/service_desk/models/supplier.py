from django.db import models

from .department import Department


class Supplier(models.Model):
    """
    Supplier Management foundation.

    Tracks supplier contact information and optional
    department ownership for scoped access.
    """

    name = models.CharField(
        max_length=200,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    contact_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    contact_email = models.EmailField(
        blank=True,
        default="",
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suppliers",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["department"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name
