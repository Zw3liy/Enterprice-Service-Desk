"""Customer self-service portal services."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.customer_portal.models import PortalAnnouncement, PortalProfile
from apps.service_desk.models import KnowledgeArticle, RequestType, Ticket
from apps.service_desk.services.knowledge_service import KnowledgeService
from apps.service_desk.services.ticket_service import TicketService


class PortalService:
    @staticmethod
    def ensure_profile(user, company) -> PortalProfile:
        profile, _ = PortalProfile.objects.get_or_create(
            user=user,
            defaults={
                "company": company,
                "display_name": user.get_full_name() or user.get_username(),
            },
        )
        if profile.company_id != company.pk:
            profile.company = company
            profile.save(update_fields=["company", "updated_at"])
        return profile

    @staticmethod
    def my_tickets(user, company=None):
        qs = TicketService.base_queryset().filter(
            Q(requester_user=user) | Q(requester__user=user)
        )
        if company:
            qs = qs.filter(company=company)
        return qs

    @staticmethod
    def catalog(company):
        return RequestType.objects.filter(
            department__company=company, is_active=True
        ).select_related("department", "default_priority", "default_queue", "sla")

    @staticmethod
    def announcements(company):
        now = timezone.now()
        qs = PortalAnnouncement.objects.filter(company=company, is_active=True)
        qs = qs.filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        qs = qs.filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        return qs

    @classmethod
    def create_request(cls, user, company, *, title, description="", request_type=None, **kwargs):
        return TicketService.create_ticket(
            title=title,
            description=description,
            company=company,
            request_type=request_type,
            department=getattr(request_type, "department", None),
            ticket_type=Ticket.TicketType.SERVICE_REQUEST,
            channel=Ticket.Channel.PORTAL,
            requester_user=user,
            actor=user,
            **kwargs,
        )

    @staticmethod
    def knowledge(company, query: str = ""):
        return KnowledgeService.search(query, company=company, include_internal=False)