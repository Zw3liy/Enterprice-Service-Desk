from django.db.models import Q, QuerySet

from apps.service_desk.models import CatalogItem


class CatalogSelector:
    """
    Read-only catalogue-item query layer.
    """

    @staticmethod
    def _base_queryset() -> "QuerySet[CatalogItem]":
        return CatalogItem.objects.select_related(
            "category",
            "fulfillment_department",
        )

    @classmethod
    def get_by_id(cls, item_id: int) -> CatalogItem:
        return cls._base_queryset().get(pk=item_id)

    @classmethod
    def get_by_category(cls, category_id: int) -> "QuerySet[CatalogItem]":
        return cls._base_queryset().filter(category_id=category_id)

    @classmethod
    def search(cls, query: str) -> "QuerySet[CatalogItem]":
        return cls._base_queryset().filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

    @classmethod
    def scoped_summary(cls, queryset: "QuerySet[CatalogItem]") -> dict:
        """
        Active/inactive counts for an already-scoped item queryset.

        Takes the queryset rather than the user so the caller's RBAC
        scoping is never bypassed here.
        """

        total = queryset.count()
        active = queryset.filter(is_active=True).count()

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
        }
