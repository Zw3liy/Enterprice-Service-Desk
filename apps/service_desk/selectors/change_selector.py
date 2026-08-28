from django.db.models import Q, QuerySet

from apps.service_desk.models import Change


class ChangeSelector:
    """
    Read-only change query layer.

    Every method here takes an already RBAC-scoped queryset (from
    ``security.policies.get_change_queryset``) rather than a user, so
    scoping can never be bypassed by calling a selector method
    directly.
    """

    @staticmethod
    def with_related(queryset: "QuerySet[Change]") -> "QuerySet[Change]":
        return queryset.select_related(
            "department",
            "requested_by",
            "assigned_to",
        )

    @classmethod
    def search(cls, queryset: "QuerySet[Change]", query: str) -> "QuerySet[Change]":
        return queryset.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    @classmethod
    def get_open(cls, queryset: "QuerySet[Change]") -> "QuerySet[Change]":
        return cls.with_related(queryset).exclude(
            status__in=[
                Change.STATUS_COMPLETED,
                Change.STATUS_REJECTED,
                Change.STATUS_ROLLED_BACK,
            ]
        )

    @classmethod
    def get_scheduled_conflicts(
        cls,
        department_id,
        start,
        end,
        exclude_pk=None,
    ) -> "QuerySet[Change]":
        """
        Changes in the same department whose scheduled window
        overlaps ``[start, end]`` and that are still scheduled or
        actively implementing — the set a new schedule must not
        collide with.
        """

        queryset = Change.objects.filter(
            department_id=department_id,
            status__in=Change.SCHEDULABLE_STATUSES,
            scheduled_start__lt=end,
            scheduled_end__gt=start,
        )

        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)

        return queryset

    @classmethod
    def scoped_summary(cls, queryset: "QuerySet[Change]") -> dict:
        return {
            "total": queryset.count(),
            "open": queryset.exclude(
                status__in=[
                    Change.STATUS_COMPLETED,
                    Change.STATUS_REJECTED,
                    Change.STATUS_ROLLED_BACK,
                ]
            ).count(),
            "awaiting_approval": queryset.filter(
                status=Change.STATUS_ASSESSED
            ).count(),
            "completed": queryset.filter(
                status=Change.STATUS_COMPLETED
            ).count(),
        }
