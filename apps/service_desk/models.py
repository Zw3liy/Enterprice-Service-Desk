"""
Enterprise Service Desk
Domain Models

Phase 2.2 Authorization Ready

Responsibilities:
- Department ownership
- Request classification
- Ticket lifecycle foundation
- User ownership
- Technician assignment
- Manager scope

Security relationships:

User
 |
 +-- created_tickets
 |
 +-- assigned_tickets
 |
 +-- managed_departments

Department
 |
 +-- managers
 |
 +-- tickets

Ticket
 |
 +-- created_by
 |
 +-- assigned_to
 |
 +-- department
"""

from django.conf import settings
from django.db import models


# ==========================================================
# Department
# ==========================================================

class Department(models.Model):
    """
    Enterprise organizational unit.

    Managers assigned here can view/manage
    tickets belonging to this department.
    """

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="managed_departments"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "name"
        ]

        indexes = [
            models.Index(
                fields=[
                    "name"
                ]
            ),
        ]

    def __str__(self):
        return self.name


# ==========================================================
# Request Type
# ==========================================================

class RequestType(models.Model):
    """
    Defines ticket categories.

    Example:
    - Incident
    - Service Request
    - Access Request
    """

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "name"
        ]

        indexes = [
            models.Index(
                fields=[
                    "name"
                ]
            ),
        ]

    def __str__(self):
        return self.name


# ==========================================================
# Ticket
# ==========================================================

class Ticket(models.Model):

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]


    URGENCY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]


    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("pending", "Pending"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]


    # ------------------------------------------------------
    # Core Information
    # ------------------------------------------------------

    title = models.CharField(
        max_length=200
    )

    description = models.TextField()


    # ------------------------------------------------------
    # Classification
    # ------------------------------------------------------

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium"
    )

    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default="medium"
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )


    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets"
    )


    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets"
    )


    # ------------------------------------------------------
    # Authorization Relationships
    # ------------------------------------------------------

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets"
    )


    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="created_tickets"
    )


    # ------------------------------------------------------
    # Metadata
    # ------------------------------------------------------

    tags = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    # ------------------------------------------------------
    # Database Configuration
    # ------------------------------------------------------

    class Meta:

        ordering = [
            "-created_at"
        ]

        indexes = [

            models.Index(
                fields=[
                    "status"
                ]
            ),

            models.Index(
                fields=[
                    "priority"
                ]
            ),

            models.Index(
                fields=[
                    "created_by"
                ]
            ),

            models.Index(
                fields=[
                    "assigned_to"
                ]
            ),

            models.Index(
                fields=[
                    "department"
                ]
            ),

        ]


    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------

    def __str__(self):

        return f"[{self.pk}] {self.title}"