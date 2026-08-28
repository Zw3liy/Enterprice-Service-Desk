from django.conf import settings
from django.db import models
from django.utils import timezone

from .department import Department
from .ticket import Ticket


class ServiceCategory(models.Model):
    """
    Top-level grouping for catalogue items.

    Administered like ``Department``/``RequestType`` — reference data
    with no dedicated app views, managed through Django admin.
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
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class CatalogItem(models.Model):
    """
    One requestable offering in the service catalogue.

    ``fulfillment_department`` is the fulfilment team a request for
    this item is routed to (mirrors ``Ticket.department``).
    ``requires_approval`` gates whether a ``ServiceRequest`` for this
    item starts in ``pending_approval`` or is auto-approved.
    ``expected_delivery_days`` is the target used to compute
    ``ServiceRequest.expected_fulfillment_date`` at request time.
    """

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="items",
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    fulfillment_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfilled_catalog_items",
    )

    requires_approval = models.BooleanField(
        default=False,
    )

    default_priority = models.CharField(
        max_length=20,
        choices=Ticket.PRIORITY_CHOICES,
        default="medium",
    )

    expected_delivery_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Target calendar days to fulfilment, shown to requesters.",
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
        ordering = ["category__name", "name"]
        verbose_name = "Catalogue Item"
        verbose_name_plural = "Catalogue Items"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_catalog_item_name_per_category",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["category"]),
            models.Index(fields=["fulfillment_department"]),
        ]

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    """
    A submitted request for a ``CatalogItem``.

    Wraps a ``Ticket`` one-to-one rather than reimplementing
    visibility, attachments, comments or audit history — RBAC for a
    ``ServiceRequest`` is derived entirely from
    ``security.policies.get_ticket_queryset`` via its ``ticket`` FK
    (see ADR-011, Decision 2: "without duplicating ticket security").
    Fields here are catalogue-specific state layered on top.
    """

    STATUS_PENDING_APPROVAL = "pending_approval"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_ASSIGNED = "assigned"
    STATUS_FULFILLING = "fulfilling"
    STATUS_FULFILLED = "fulfilled"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING_APPROVAL, "Pending Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_FULFILLING, "Fulfilling"),
        (STATUS_FULFILLED, "Fulfilled"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    OPEN_STATUSES = {
        STATUS_PENDING_APPROVAL,
        STATUS_APPROVED,
        STATUS_ASSIGNED,
        STATUS_FULFILLING,
    }

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name="service_request",
    )

    catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.PROTECT,
        related_name="requests",
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    justification = models.TextField(
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_APPROVAL,
        db_index=True,
    )

    expected_fulfillment_date = models.DateField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["catalog_item"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"SR-{self.pk}: {self.catalog_item.name}"

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES


class ServiceRequestApproval(models.Model):
    """
    One approval decision on a ``ServiceRequest``.

    Append-only: a decision is never edited, only superseded by the
    status it produced. Separation of duties (the approver may not be
    the requester) is enforced in ``ServiceRequestService``, not here.
    """

    DECISION_APPROVED = "approved"
    DECISION_REJECTED = "rejected"

    DECISION_CHOICES = [
        (DECISION_APPROVED, "Approved"),
        (DECISION_REJECTED, "Rejected"),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_request_approvals",
    )

    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
    )

    comment = models.TextField(
        blank=True,
        default="",
    )

    decided_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-decided_at"]
        verbose_name = "Service Request Approval"
        verbose_name_plural = "Service Request Approvals"
        indexes = [
            models.Index(fields=["service_request", "decided_at"]),
        ]

    def __str__(self):
        return f"{self.service_request} - {self.get_decision_display()}"


class ServiceRequestHistory(models.Model):
    """
    Immutable audit trail for service-request-specific events.

    Complements ``TicketHistory`` on the underlying ticket; this
    model records only catalogue-workflow events (approval, rejection,
    fulfilment stages, cancellation) that have no equivalent in the
    generic ticket lifecycle.
    """

    EVENT_CREATED = "created"
    EVENT_APPROVED = "approved"
    EVENT_REJECTED = "rejected"
    EVENT_ASSIGNED = "assigned"
    EVENT_FULFILLING = "fulfilling"
    EVENT_FULFILLED = "fulfilled"
    EVENT_CANCELLED = "cancelled"

    EVENT_CHOICES = [
        (EVENT_CREATED, "Created"),
        (EVENT_APPROVED, "Approved"),
        (EVENT_REJECTED, "Rejected"),
        (EVENT_ASSIGNED, "Assigned"),
        (EVENT_FULFILLING, "Fulfilling"),
        (EVENT_FULFILLED, "Fulfilled"),
        (EVENT_CANCELLED, "Cancelled"),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_request_history",
    )

    old_value = models.TextField(
        blank=True,
        default="",
    )

    new_value = models.TextField(
        blank=True,
        default="",
    )

    comment = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Service Request History"
        verbose_name_plural = "Service Request History"
        indexes = [
            models.Index(fields=["service_request", "created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.service_request} - {self.get_event_type_display()}"

    @classmethod
    def record(
        cls,
        *,
        service_request,
        event_type,
        user=None,
        comment="",
        old_value="",
        new_value="",
        metadata=None,
    ):
        return cls.objects.create(
            service_request=service_request,
            event_type=event_type,
            performed_by=user,
            comment=comment,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )
