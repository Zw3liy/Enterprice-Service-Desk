"""Identity provisioning from SSO assertions."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.service_desk.models import AgentProfile, Company, Contact

logger = logging.getLogger(__name__)
User = get_user_model()


class IdentityService:
    @classmethod
    @transaction.atomic
    def upsert_from_sso(
        cls,
        *,
        email: str,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
        company: Company | None = None,
        is_staff: bool = False,
        groups: list[str] | None = None,
    ):
        username = username or email.split("@")[0]
        user, created = User.objects.get_or_create(
            username=username[:150],
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": is_staff,
            },
        )
        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            changed = True
        if is_staff and not user.is_staff:
            user.is_staff = True
            changed = True
        if changed:
            user.save()
        if company is not None:
            Contact.objects.update_or_create(
                company=company,
                email=email,
                defaults={
                    "user": user,
                    "first_name": first_name or user.first_name or username,
                    "last_name": last_name or user.last_name,
                    "is_active": True,
                },
            )
            if is_staff or (groups and any("agent" in g.lower() for g in groups)):
                AgentProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "company": company,
                        "display_name": user.get_full_name() or username,
                        "is_available": True,
                    },
                )
        logger.info("sso_upsert user=%s created=%s", user.username, created)
        return user