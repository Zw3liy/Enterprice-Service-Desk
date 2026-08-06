from typing import Any

from django.db.models import Count, Q, QuerySet

from apps.service_desk.models import Ticket


class TicketSelector:
    """
    Read-only data access layer for Ticket queries.

    This class contains optimized queries only.
    No business logic or write operations should exist here.
    """

    @staticmethod
    def _base_queryset() -> QuerySet[Ticket]:
        """
        Base optimized queryset used by all selectors.
        """
        return (
            Ticket.objects.select_related(
                "department",
                "request_type",
                "created_by",
                "assigned_to",
            )
            .prefetch_related("history")
            .order_by("-created_at")
        )

    @classmethod
    def get_by_id(cls, ticket_id: int) -> Ticket:
        """
        Retrieve a single ticket by primary key.

        Raises:
            Ticket.DoesNotExist
        """
        return cls._base_queryset().get(pk=ticket_id)

    @classmethod
    def get_by_status(cls, status: str) -> QuerySet[Ticket]:
        """
        Retrieve tickets by status.
        """
        return cls._base_queryset().filter(status=status)

    @classmethod
    def get_by_priority(cls, priority: str) -> QuerySet[Ticket]:
        """
        Retrieve tickets by priority.
        """
        return cls._base_queryset().filter(priority=priority)

    @classmethod
    def get_by_department(cls, department_id: int) -> QuerySet[Ticket]:
        """
        Retrieve tickets belonging to a department.
        """
        return cls._base_queryset().filter(department_id=department_id)

    @classmethod
    def get_by_request_type(cls, request_type_id: int) -> QuerySet[Ticket]:
        """
        Retrieve tickets by request type.
        """
        return cls._base_queryset().filter(request_type_id=request_type_id)

    @classmethod
    def get_by_creator(cls, user_id: int) -> QuerySet[Ticket]:
        """
        Retrieve tickets created by a user.
        """
        return cls._base_queryset().filter(created_by_id=user_id)

    @classmethod
    def get_by_assignee(cls, user_id: int) -> QuerySet[Ticket]:
        """
        Retrieve tickets assigned to a technician.
        """
        return cls._base_queryset().filter(assigned_to_id=user_id)

    @classmethod
    def get_open_tickets(cls) -> QuerySet[Ticket]:
        """
        Retrieve all open tickets.
        """
        return cls._base_queryset().filter(status="open")

    @classmethod
    def get_closed_tickets(cls) -> QuerySet[Ticket]:
        """
        Retrieve all closed tickets.
        """
        return cls._base_queryset().filter(status="closed")

    @classmethod
    def get_resolved_tickets(cls) -> QuerySet[Ticket]:
        """
        Retrieve all resolved tickets.
        """
        return cls._base_queryset().filter(status="resolved")

    @classmethod
    def get_recent_tickets(cls, limit: int = 10) -> QuerySet[Ticket]:
        """
        Retrieve most recent tickets.
        """
        return cls._base_queryset()[:limit]

    @classmethod
    def search(cls, query: str) -> QuerySet[Ticket]:
        """
        Full ticket search.
        """
        return cls._base_queryset().filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )

    @classmethod
    def dashboard_statistics(cls) -> dict[str, Any]:
        """
        Dashboard metrics.
        """
        queryset = Ticket.objects.all()

        stats = queryset.aggregate(
            total_tickets=Count("id"),
            open_tickets=Count("id", filter=Q(status="open")),
            in_progress_tickets=Count(
                "id",
                filter=Q(status="in_progress"),
            ),
            pending_tickets=Count(
                "id",
                filter=Q(status="pending"),
            ),
            resolved_tickets=Count(
                "id",
                filter=Q(status="resolved"),
            ),
            closed_tickets=Count(
                "id",
                filter=Q(status="closed"),
            ),
            high_priority_tickets=Count(
                "id",
                filter=Q(priority="high"),
            ),
            urgent_priority_tickets=Count(
                "id",
                filter=Q(priority="urgent"),
            ),
        )

        return stats