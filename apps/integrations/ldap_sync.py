"""LDAP / Active Directory user sync helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.service_desk.models import AgentProfile, Company, Contact

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass
class LDAPUser:
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_agent: bool = False
    department: str = ""
    title: str = ""


class LDAPSyncService:
    """
    Provider-agnostic sync. Pass already-fetched LDAPUser records from your
    connector (ldap3 / python-ldap). Keeps this module free of optional C deps.
    """

    @classmethod
    @transaction.atomic
    def sync_users(
        cls,
        company: Company,
        users: Iterable[LDAPUser],
        *,
        deactivate_missing: bool = False,
    ) -> dict:
        seen_usernames: set[str] = set()
        created = updated = 0
        for entry in users:
            username = (entry.username or entry.email.split("@")[0])[:150]
            seen_usernames.add(username)
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": entry.email,
                    "first_name": entry.first_name,
                    "last_name": entry.last_name,
                    "is_active": entry.is_active,
                    "is_staff": entry.is_agent,
                },
            )
            if was_created:
                created += 1
                user.set_unusable_password()
                user.save()
            else:
                fields = []
                for attr, value in [
                    ("email", entry.email),
                    ("first_name", entry.first_name),
                    ("last_name", entry.last_name),
                    ("is_active", entry.is_active),
                ]:
                    if getattr(user, attr) != value and value != "":
                        setattr(user, attr, value)
                        fields.append(attr)
                if entry.is_agent and not user.is_staff:
                    user.is_staff = True
                    fields.append("is_staff")
                if fields:
                    user.save(update_fields=fields)
                    updated += 1
            if entry.email:
                Contact.objects.update_or_create(
                    company=company,
                    email=entry.email,
                    defaults={
                        "user": user,
                        "first_name": entry.first_name or username,
                        "last_name": entry.last_name,
                        "job_title": entry.title,
                        "is_active": entry.is_active,
                    },
                )
            if entry.is_agent:
                AgentProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "company": company,
                        "display_name": user.get_full_name() or username,
                        "is_available": entry.is_active,
                    },
                )
        deactivated = 0
        if deactivate_missing:
            qs = User.objects.exclude(username__in=seen_usernames).filter(
                agent_profile__company=company, is_superuser=False
            )
            deactivated = qs.update(is_active=False)
        result = {
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
            "seen": len(seen_usernames),
        }
        logger.info("ldap_sync company=%s result=%s", company.slug, result)
        return result
