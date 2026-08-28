from django.conf import settings
from django.db import models

from .change import Change
from .department import Department
from .ticket import Ticket


class ConfigurationItemType(models.Model):
    """
    Defines CI categories (server, network device, application,
    database, ...).

    Administered like ``Department``/``RequestType``/``ServiceCategory``
    — reference data with no dedicated app views, managed through
    Django admin.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Configuration Item Type"
        verbose_name_plural = "Configuration Item Types"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class ConfigurationItem(models.Model):
    """
    One asset/CI in the CMDB.

    ``tickets``/``changes`` link a CI to the tickets and changes it
    is relevant to — a plain M2M defined here (not by adding a field
    to ``Ticket``/``Change``) so those established, tested models
    stay untouched.
    """

    STATUS_IN_SERVICE = "in_service"
    STATUS_IN_REPAIR = "in_repair"
    STATUS_IN_STOCK = "in_stock"
    STATUS_RETIRED = "retired"
    STATUS_DISPOSED = "disposed"

    STATUS_CHOICES = [
        (STATUS_IN_SERVICE, "In Service"),
        (STATUS_IN_REPAIR, "In Repair"),
        (STATUS_IN_STOCK, "In Stock"),
        (STATUS_RETIRED, "Retired"),
        (STATUS_DISPOSED, "Disposed"),
    ]

    CRITICALITY_LOW = "low"
    CRITICALITY_MEDIUM = "medium"
    CRITICALITY_HIGH = "high"
    CRITICALITY_CRITICAL = "critical"

    CRITICALITY_CHOICES = [
        (CRITICALITY_LOW, "Low"),
        (CRITICALITY_MEDIUM, "Medium"),
        (CRITICALITY_HIGH, "High"),
        (CRITICALITY_CRITICAL, "Critical"),
    ]

    ci_type = models.ForeignKey(
        ConfigurationItemType,
        on_delete=models.PROTECT,
        related_name="items",
    )

    name = models.CharField(
        max_length=200,
    )

    identifier = models.CharField(
        max_length=100,
        unique=True,
        help_text="Asset tag, serial number, or other unique identifier.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_SERVICE,
        db_index=True,
    )

    criticality = models.CharField(
        max_length=20,
        choices=CRITICALITY_CHOICES,
        default=CRITICALITY_MEDIUM,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configuration_items",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_configuration_items",
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    tickets = models.ManyToManyField(
        Ticket,
        blank=True,
        related_name="configuration_items",
    )

    changes = models.ManyToManyField(
        Change,
        blank=True,
        related_name="configuration_items",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Configuration Item"
        verbose_name_plural = "Configuration Items"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["criticality"]),
            models.Index(fields=["department"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["ci_type"]),
            models.Index(fields=["identifier"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.identifier})"


class CIRelationship(models.Model):
    """
    A directed relationship between two configuration items.

    "Validated relationship types" per the mission spec: the type is
    a fixed, closed choice set, not free text. Self-relationships and
    duplicate (source, target, type) triples are rejected at both the
    database (constraints below) and service layer
    (``CMDBService.add_relationship``).
    """

    TYPE_DEPENDS_ON = "depends_on"
    TYPE_CONNECTS_TO = "connects_to"
    TYPE_HOSTS = "hosts"
    TYPE_RUNS_ON = "runs_on"
    TYPE_PART_OF = "part_of"
    TYPE_BACKS_UP = "backs_up"

    TYPE_CHOICES = [
        (TYPE_DEPENDS_ON, "Depends On"),
        (TYPE_CONNECTS_TO, "Connects To"),
        (TYPE_HOSTS, "Hosts"),
        (TYPE_RUNS_ON, "Runs On"),
        (TYPE_PART_OF, "Part Of"),
        (TYPE_BACKS_UP, "Backs Up"),
    ]

    source = models.ForeignKey(
        ConfigurationItem,
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )

    target = models.ForeignKey(
        ConfigurationItem,
        on_delete=models.CASCADE,
        related_name="incoming_relationships",
    )

    relationship_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ci_relationships",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CI Relationship"
        verbose_name_plural = "CI Relationships"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source=models.F("target")),
                name="ci_relationship_no_self_reference",
            ),
            models.UniqueConstraint(
                fields=["source", "target", "relationship_type"],
                name="unique_ci_relationship",
            ),
        ]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["target"]),
            models.Index(fields=["relationship_type"]),
        ]

    def __str__(self):
        return f"{self.source} -{self.get_relationship_type_display()}-> {self.target}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.source_id is not None and self.source_id == self.target_id:
            raise ValidationError(
                "A configuration item cannot have a relationship with itself."
            )
