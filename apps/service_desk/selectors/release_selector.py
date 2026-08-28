from django.db.models import Q, QuerySet

from apps.service_desk.models import Release


class ReleaseSelector:
    """
    Read-only release query layer.

    Every method here takes an already RBAC-scoped queryset (from
    ``security.policies.get_release_queryset``) rather than a user,
    so scoping can never be bypassed by calling a selector method
    directly.
    """

    @staticmethod
    def with_related(queryset: "QuerySet[Release]") -> "QuerySet[Release]":
        return queryset.select_related(
            "department",
            "owner",
        ).prefetch_related("changes")

    @classmethod
    def search(cls, queryset: "QuerySet[Release]", query: str) -> "QuerySet[Release]":
        return queryset.filter(
            Q(name__icontains=query) | Q(version__icontains=query)
        )

    @classmethod
    def get_scheduled_conflicts(
        cls,
        department_id,
        environment,
        start,
        end,
        exclude_pk=None,
    ) -> "QuerySet[Release]":
        """
        Releases in the same department and environment whose
        scheduled window overlaps ``[start, end]`` and that are still
        scheduled or actively deploying.
        """

        queryset = Release.objects.filter(
            department_id=department_id,
            environment=environment,
            status__in=Release.SCHEDULABLE_STATUSES,
            scheduled_start__lt=end,
            scheduled_end__gt=start,
        )

        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)

        return queryset

    @classmethod
    def scoped_summary(cls, queryset: "QuerySet[Release]") -> dict:
        return {
            "total": queryset.count(),
            "open": queryset.exclude(
                status__in=[
                    Release.STATUS_COMPLETED,
                    Release.STATUS_ROLLED_BACK,
                ]
            ).count(),
            "completed": queryset.filter(
                status=Release.STATUS_COMPLETED
            ).count(),
        }
