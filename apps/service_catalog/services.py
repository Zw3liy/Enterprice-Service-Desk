from __future__ import annotations

from apps.customer_portal.services import PortalService
from apps.service_desk.models import RequestType


class ServiceCatalogService:
    @staticmethod
    def list_items(company):
        return PortalService.catalog(company)

    @staticmethod
    def get_item(company, code: str) -> RequestType | None:
        return RequestType.objects.filter(
            department__company=company, code=code, is_active=True
        ).first()

    @classmethod
    def request_item(cls, user, company, code: str, *, title: str, description: str = ""):
        item = cls.get_item(company, code)
        return PortalService.create_request(
            user,
            company,
            title=title,
            description=description,
            request_type=item,
        )
