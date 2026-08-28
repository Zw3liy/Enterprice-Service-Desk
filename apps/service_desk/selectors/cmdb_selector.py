from django.db.models import Q, QuerySet

from apps.service_desk.models import ConfigurationItem


class CMDBSelector:
    """
    Read-only CMDB query layer.

    Every method here takes an already RBAC-scoped queryset (from
    ``security.policies.get_configuration_item_queryset``) rather
    than a user, so scoping can never be bypassed by calling a
    selector method directly.
    """

    @staticmethod
    def with_related(queryset: "QuerySet[ConfigurationItem]") -> "QuerySet[ConfigurationItem]":
        return queryset.select_related(
            "ci_type",
            "department",
            "owner",
        )

    @classmethod
    def search(cls, queryset: "QuerySet[ConfigurationItem]", query: str) -> "QuerySet[ConfigurationItem]":
        return queryset.filter(
            Q(name__icontains=query)
            | Q(identifier__icontains=query)
            | Q(description__icontains=query)
        )

    @classmethod
    def scoped_summary(cls, queryset: "QuerySet[ConfigurationItem]") -> dict:
        return {
            "total": queryset.count(),
            "in_service": queryset.filter(
                status=ConfigurationItem.STATUS_IN_SERVICE
            ).count(),
            "critical": queryset.filter(
                criticality=ConfigurationItem.CRITICALITY_CRITICAL
            ).count(),
        }
