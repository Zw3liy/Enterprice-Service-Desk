from django.db.models import QuerySet

from apps.service_desk.models import ServiceRequest


class ServiceRequestSelector:
    """
    Read-only service-request query layer.

    Every method here takes an already RBAC-scoped queryset (from
    ``security.policies.get_service_request_queryset``) rather than a
    user, so scoping can never be bypassed by calling a selector
    method directly.
    """

    @staticmethod
    def with_related(queryset: "QuerySet[ServiceRequest]") -> "QuerySet[ServiceRequest]":
        return queryset.select_related(
            "ticket",
            "ticket__created_by",
            "ticket__assigned_to",
            "ticket__department",
            "catalog_item",
            "catalog_item__category",
        )

    @classmethod
    def get_open(cls, queryset: "QuerySet[ServiceRequest]") -> "QuerySet[ServiceRequest]":
        return cls.with_related(queryset).filter(
            status__in=ServiceRequest.OPEN_STATUSES
        )

    @classmethod
    def get_pending_approval(cls, queryset: "QuerySet[ServiceRequest]") -> "QuerySet[ServiceRequest]":
        return cls.with_related(queryset).filter(
            status=ServiceRequest.STATUS_PENDING_APPROVAL
        )

    @classmethod
    def scoped_summary(cls, queryset: "QuerySet[ServiceRequest]") -> dict:
        return {
            "total": queryset.count(),
            "pending_approval": queryset.filter(
                status=ServiceRequest.STATUS_PENDING_APPROVAL
            ).count(),
            "open": queryset.filter(
                status__in=ServiceRequest.OPEN_STATUSES
            ).count(),
            "fulfilled": queryset.filter(
                status=ServiceRequest.STATUS_FULFILLED
            ).count(),
        }
