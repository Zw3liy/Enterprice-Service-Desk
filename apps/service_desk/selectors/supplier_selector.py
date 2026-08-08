from django.db.models import Q, QuerySet

from apps.service_desk.models import Supplier


class SupplierSelector:
    """
    Read-only supplier query layer.
    """

    @staticmethod
    def _base_queryset() -> QuerySet[Supplier]:
        return Supplier.objects.select_related(
            "department",
        ).order_by("name")

    @classmethod
    def get_by_id(cls, supplier_id: int) -> Supplier:
        return cls._base_queryset().get(pk=supplier_id)

    @classmethod
    def get_active_suppliers(cls) -> QuerySet[Supplier]:
        return cls._base_queryset().filter(is_active=True)

    @classmethod
    def get_by_department(cls, department_id: int) -> QuerySet[Supplier]:
        return cls._base_queryset().filter(department_id=department_id)

    @classmethod
    def search(cls, query: str) -> QuerySet[Supplier]:
        return cls._base_queryset().filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(contact_name__icontains=query)
            | Q(contact_email__icontains=query)
        )
