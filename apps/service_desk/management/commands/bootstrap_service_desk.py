"""
Idempotent Enterprise Service Desk master-data bootstrap.

Usage examples:

    python manage.py bootstrap_service_desk --dry-run
    python manage.py bootstrap_service_desk --update-existing
    python manage.py bootstrap_service_desk --skip-users
    python manage.py bootstrap_service_desk \\
        --admin-username admin \\
        --admin-email admin@example.com

Passwords are never hardcoded. Supply them via environment variables
(preferred) or interactive prompt when a user is being created:

    BOOTSTRAP_ADMIN_PASSWORD
    BOOTSTRAP_MANAGER_PASSWORD
    BOOTSTRAP_TECHNICIAN_PASSWORD
    BOOTSTRAP_REQUESTER_PASSWORD

Or a shared fallback:

    BOOTSTRAP_INITIAL_PASSWORD

Passwords are hashed by Django's user manager and never written to logs.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from getpass import getpass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.service_desk.models import Department, RequestType, SLAPolicy
from apps.service_desk.services.sla_service import SLAService

User = get_user_model()


# ---------------------------------------------------------------------------
# Canonical master data
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    {
        "name": "Information Technology",
        "description": "IT infrastructure, applications and end-user support.",
    },
    {
        "name": "Human Resources",
        "description": "People operations, onboarding and employee services.",
    },
    {
        "name": "Finance",
        "description": "Financial operations, accounts and procurement support.",
    },
    {
        "name": "Operations",
        "description": "Day-to-day business operations and process support.",
    },
    {
        "name": "Facilities",
        "description": "Building, workspace and physical plant services.",
    },
    {
        "name": "Procurement",
        "description": "Purchasing, vendor coordination and supply chain.",
    },
    {
        "name": "Security",
        "description": "Information security, physical security and compliance.",
    },
    {
        "name": "Customer Support",
        "description": "External customer service and support operations.",
    },
]


# Request types are global in the current schema (no department FK). The
# ``default_department`` key is retained only as documentation of the
# intended routing target for operators; it is not persisted.
REQUEST_TYPES = [
    {
        "name": "Incident",
        "description": "Unplanned interruption or degradation of a service.",
        "default_department": "Information Technology",
    },
    {
        "name": "Service Request",
        "description": "Standard request for a service or change of state.",
        "default_department": "Information Technology",
    },
    {
        "name": "Access Request",
        "description": "Request for system, application or facility access.",
        "default_department": "Information Technology",
    },
    {
        "name": "Hardware Request",
        "description": "Request for hardware provision or replacement.",
        "default_department": "Information Technology",
    },
    {
        "name": "Software Request",
        "description": "Request for software installation or licence.",
        "default_department": "Information Technology",
    },
    {
        "name": "Network Request",
        "description": "Network connectivity, VPN or firewall request.",
        "default_department": "Information Technology",
    },
    {
        "name": "Security Incident",
        "description": "Suspected or confirmed security event requiring response.",
        "default_department": "Security",
    },
    {
        "name": "General Enquiry",
        "description": "General question that does not fit another category.",
        "default_department": "Customer Support",
    },
]


# Ticket.PRIORITY_CHOICES uses ``urgent`` for the highest priority. The
# operator-facing label "Critical" maps onto that stored value.
SLA_POLICIES = [
    {
        "name": "Critical Priority Default",
        "priority": "urgent",
        "response_minutes": 15,
        "resolution_minutes": 240,
        "warning_threshold_percent": 75,
    },
    {
        "name": "High Priority Default",
        "priority": "high",
        "response_minutes": 60,
        "resolution_minutes": 480,
        "warning_threshold_percent": 80,
    },
    {
        "name": "Medium Priority Default",
        "priority": "medium",
        "response_minutes": 240,
        "resolution_minutes": 1440,
        "warning_threshold_percent": 80,
    },
    {
        "name": "Low Priority Default",
        "priority": "low",
        "response_minutes": 480,
        "resolution_minutes": 4320,
        "warning_threshold_percent": 85,
    },
]


ROLE_USER_SPECS = (
    {
        "role": "Administrator",
        "flag": "admin",
        "username_opt": "admin_username",
        "email_opt": "admin_email",
        "default_username": "sd_admin",
        "default_email": "admin@example.com",
        "password_env": ("BOOTSTRAP_ADMIN_PASSWORD",),
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "role": "Manager",
        "flag": "manager",
        "username_opt": "manager_username",
        "email_opt": "manager_email",
        "default_username": "sd_manager",
        "default_email": "manager@example.com",
        "password_env": ("BOOTSTRAP_MANAGER_PASSWORD",),
        "is_staff": False,
        "is_superuser": False,
        "manage_department": "Information Technology",
    },
    {
        "role": "Technician",
        "flag": "technician",
        "username_opt": "technician_username",
        "email_opt": "technician_email",
        "default_username": "sd_technician",
        "default_email": "technician@example.com",
        "password_env": ("BOOTSTRAP_TECHNICIAN_PASSWORD",),
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "role": "Requester",
        "flag": "requester",
        "username_opt": "requester_username",
        "email_opt": "requester_email",
        "default_username": "sd_requester",
        "default_email": "requester@example.com",
        "password_env": ("BOOTSTRAP_REQUESTER_PASSWORD",),
        "is_staff": False,
        "is_superuser": False,
    },
)


@dataclass
class BootstrapResult:
    """Structured, password-free summary of a bootstrap run."""

    dry_run: bool = False
    update_existing: bool = False
    skip_users: bool = False
    departments: dict[str, int] = field(
        default_factory=lambda: {"created": 0, "updated": 0, "skipped": 0}
    )
    request_types: dict[str, int] = field(
        default_factory=lambda: {"created": 0, "updated": 0, "skipped": 0}
    )
    sla_policies: dict[str, int] = field(
        default_factory=lambda: {"created": 0, "updated": 0, "skipped": 0}
    )
    roles: dict[str, int] = field(
        default_factory=lambda: {"created": 0, "updated": 0, "skipped": 0}
    )
    users: dict[str, int] = field(
        default_factory=lambda: {"created": 0, "updated": 0, "skipped": 0}
    )
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "update_existing": self.update_existing,
            "skip_users": self.skip_users,
            "departments": dict(self.departments),
            "request_types": dict(self.request_types),
            "sla_policies": dict(self.sla_policies),
            "roles": dict(self.roles),
            "users": dict(self.users),
            "errors": list(self.errors),
        }


class Command(BaseCommand):
    help = (
        "Idempotently bootstrap Service Desk master data: departments, "
        "request types, SLA policies, RBAC roles and optional seed users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help=(
                "Update description/targets on records that already exist. "
                "Without this flag existing records are left untouched."
            ),
        )
        parser.add_argument(
            "--skip-users",
            action="store_true",
            help="Do not create or update any seed users.",
        )
        parser.add_argument(
            "--admin-username",
            default=None,
            help="Username for the initial Administrator user.",
        )
        parser.add_argument(
            "--admin-email",
            default=None,
            help="Email for the initial Administrator user.",
        )
        parser.add_argument(
            "--manager-username",
            default=None,
            help="Username for the initial Manager user.",
        )
        parser.add_argument(
            "--manager-email",
            default=None,
            help="Email for the initial Manager user.",
        )
        parser.add_argument(
            "--technician-username",
            default=None,
            help="Username for the initial Technician user.",
        )
        parser.add_argument(
            "--technician-email",
            default=None,
            help="Email for the initial Technician user.",
        )
        parser.add_argument(
            "--requester-username",
            default=None,
            help="Username for the initial Requester user.",
        )
        parser.add_argument(
            "--requester-email",
            default=None,
            help="Email for the initial Requester user.",
        )
        parser.add_argument(
            "--create-seed-users",
            action="store_true",
            help=(
                "Explicitly create the four seed users (admin/manager/"
                "technician/requester). Without this flag users are only "
                "created when a username option or matching env password "
                "is supplied."
            ),
        )

    def handle(self, *args, **options):
        result = BootstrapResult(
            dry_run=bool(options["dry_run"]),
            update_existing=bool(options["update_existing"]),
            skip_users=bool(options["skip_users"]),
        )

        try:
            if result.dry_run:
                # Dry-run still uses a transaction so any accidental write
                # is rolled back, and so callers observe a consistent
                # "no side effects" guarantee.
                with transaction.atomic():
                    self._run(result, options)
                    transaction.set_rollback(True)
            else:
                with transaction.atomic():
                    self._run(result, options)
        except Exception as exc:  # pragma: no cover - surfaced below
            result.errors.append(str(exc))
            raise CommandError(f"Bootstrap failed and was rolled back: {exc}") from exc

        self._report(result)
        return result

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def _run(self, result: BootstrapResult, options: dict[str, Any]) -> None:
        self._bootstrap_departments(result)
        self._bootstrap_request_types(result)
        self._bootstrap_sla_policies(result)
        self._bootstrap_roles(result)

        if not result.skip_users:
            self._bootstrap_users(result, options)

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------

    def _bootstrap_departments(self, result: BootstrapResult) -> None:
        for spec in DEPARTMENTS:
            existing = Department.objects.filter(name=spec["name"]).first()

            if existing is None:
                if not result.dry_run:
                    Department.objects.create(
                        name=spec["name"],
                        description=spec["description"],
                    )
                result.departments["created"] += 1
                continue

            if result.update_existing and existing.description != spec["description"]:
                if not result.dry_run:
                    existing.description = spec["description"]
                    existing.save(update_fields=["description"])
                result.departments["updated"] += 1
            else:
                result.departments["skipped"] += 1

    # ------------------------------------------------------------------
    # Request types
    # ------------------------------------------------------------------

    def _bootstrap_request_types(self, result: BootstrapResult) -> None:
        for spec in REQUEST_TYPES:
            existing = RequestType.objects.filter(name=spec["name"]).first()

            if existing is None:
                if not result.dry_run:
                    RequestType.objects.create(
                        name=spec["name"],
                        description=spec["description"],
                        is_active=True,
                    )
                result.request_types["created"] += 1
                continue

            changed = False
            if result.update_existing:
                if existing.description != spec["description"]:
                    existing.description = spec["description"]
                    changed = True
                if not existing.is_active:
                    existing.is_active = True
                    changed = True

            if changed:
                if not result.dry_run:
                    existing.save()
                result.request_types["updated"] += 1
            else:
                result.request_types["skipped"] += 1

    # ------------------------------------------------------------------
    # SLA policies
    # ------------------------------------------------------------------

    def _bootstrap_sla_policies(self, result: BootstrapResult) -> None:
        for spec in SLA_POLICIES:
            existing = SLAPolicy.objects.filter(name=spec["name"]).first()

            # Prefer the unique (priority, department=None) key so a renamed
            # default cannot create a duplicate global policy for the same
            # priority.
            if existing is None:
                existing = SLAPolicy.objects.filter(
                    priority=spec["priority"],
                    department__isnull=True,
                ).first()

            if existing is None:
                if not result.dry_run:
                    SLAService.create_policy(
                        name=spec["name"],
                        priority=spec["priority"],
                        department=None,
                        response_minutes=spec["response_minutes"],
                        resolution_minutes=spec["resolution_minutes"],
                        warning_threshold_percent=spec[
                            "warning_threshold_percent"
                        ],
                        is_active=True,
                    )
                result.sla_policies["created"] += 1
                continue

            if not result.update_existing:
                result.sla_policies["skipped"] += 1
                continue

            dirty = False
            for field_name in (
                "name",
                "response_minutes",
                "resolution_minutes",
                "warning_threshold_percent",
            ):
                if getattr(existing, field_name) != spec[field_name]:
                    setattr(existing, field_name, spec[field_name])
                    dirty = True

            if not existing.is_active:
                existing.is_active = True
                dirty = True

            if dirty:
                if not result.dry_run:
                    SLAService.update_policy(
                        existing,
                        name=existing.name,
                        response_minutes=existing.response_minutes,
                        resolution_minutes=existing.resolution_minutes,
                        warning_threshold_percent=(
                            existing.warning_threshold_percent
                        ),
                        is_active=True,
                    )
                result.sla_policies["updated"] += 1
            else:
                result.sla_policies["skipped"] += 1

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------

    def _bootstrap_roles(self, result: BootstrapResult) -> None:
        from django.contrib.auth.models import Group

        before = {
            name: set(Group.objects.get(name=name).permissions.values_list(
                "id", flat=True
            ))
            if Group.objects.filter(name=name).exists()
            else None
            for name in (
                "Administrator",
                "Manager",
                "Technician",
                "Requester",
            )
        }

        if not result.dry_run:
            # Reuse the existing create_roles command so there is a single
            # source of truth for permission matrices.
            call_command("create_roles", verbosity=0)

        for name, previous in before.items():
            if result.dry_run:
                if previous is None:
                    result.roles["created"] += 1
                else:
                    result.roles["updated" if result.update_existing else "skipped"] += 1
                continue

            group = Group.objects.filter(name=name).first()
            if group is None:
                result.roles["skipped"] += 1
                continue

            current = set(group.permissions.values_list("id", flat=True))
            if previous is None:
                result.roles["created"] += 1
            elif current != previous:
                result.roles["updated"] += 1
            else:
                result.roles["skipped"] += 1

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _bootstrap_users(
        self, result: BootstrapResult, options: dict[str, Any]
    ) -> None:
        from django.contrib.auth.models import Group

        create_all = bool(options.get("create_seed_users"))

        for spec in ROLE_USER_SPECS:
            username = options.get(spec["username_opt"]) or (
                spec["default_username"] if create_all else None
            )
            email = options.get(spec["email_opt"]) or (
                spec["default_email"] if create_all else None
            )

            # A password env alone is not enough without a username; require
            # either an explicit username option or --create-seed-users.
            if not username:
                # Still honour an explicitly supplied username option of "" as skip.
                if options.get(spec["username_opt"]) is not None:
                    continue
                # Auto-create only when --create-seed-users is set.
                continue

            password = self._resolve_password(spec, create_all=create_all)

            existing = User.objects.filter(username=username).first()

            if existing is None:
                if not password:
                    raise CommandError(
                        f"Password required to create user '{username}'. "
                        f"Set one of {', '.join(spec['password_env'])} or "
                        "BOOTSTRAP_INITIAL_PASSWORD."
                    )

                if not result.dry_run:
                    user = User.objects.create_user(
                        username=username,
                        email=email or "",
                        password=password,
                    )
                    user.is_staff = spec["is_staff"]
                    user.is_superuser = spec["is_superuser"]
                    user.save(update_fields=["is_staff", "is_superuser"])

                    group = Group.objects.get(name=spec["role"])
                    user.groups.add(group)

                    manage_dept = spec.get("manage_department")
                    if manage_dept:
                        department = Department.objects.filter(
                            name=manage_dept
                        ).first()
                        if department is not None:
                            department.managers.add(user)
                result.users["created"] += 1
                continue

            if not result.update_existing:
                result.users["skipped"] += 1
                continue

            if not result.dry_run:
                dirty_fields = []
                if email and existing.email != email:
                    existing.email = email
                    dirty_fields.append("email")
                if existing.is_staff != spec["is_staff"]:
                    existing.is_staff = spec["is_staff"]
                    dirty_fields.append("is_staff")
                if existing.is_superuser != spec["is_superuser"]:
                    existing.is_superuser = spec["is_superuser"]
                    dirty_fields.append("is_superuser")
                if dirty_fields:
                    existing.save(update_fields=dirty_fields)

                if password:
                    existing.set_password(password)
                    existing.save(update_fields=["password"])

                group = Group.objects.get(name=spec["role"])
                existing.groups.add(group)

                manage_dept = spec.get("manage_department")
                if manage_dept:
                    department = Department.objects.filter(
                        name=manage_dept
                    ).first()
                    if department is not None:
                        department.managers.add(existing)

            result.users["updated"] += 1

    def _resolve_password(
        self, spec: dict[str, Any], *, create_all: bool
    ) -> str | None:
        for env_name in spec["password_env"]:
            value = os.environ.get(env_name)
            if value:
                return value

        shared = os.environ.get("BOOTSTRAP_INITIAL_PASSWORD")
        if shared:
            return shared

        # Interactive prompt only when stdin is a TTY and we are actually
        # about to create users (never in CI / non-interactive runs).
        if create_all and sys.stdin.isatty() and not os.environ.get("CI"):
            return getpass(
                f"Password for {spec['role']} user "
                f"({spec['default_username']}): "
            )

        return None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _report(self, result: BootstrapResult) -> None:
        mode = "DRY-RUN" if result.dry_run else "APPLY"
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== Service Desk Bootstrap ({mode}) ==="
        ))

        def line(label: str, counts: dict[str, int]) -> None:
            self.stdout.write(
                f"  {label:16s}  "
                f"created={counts['created']}  "
                f"updated={counts['updated']}  "
                f"skipped={counts['skipped']}"
            )

        line("Departments", result.departments)
        line("Request types", result.request_types)
        line("SLA policies", result.sla_policies)
        line("Roles", result.roles)
        line("Users", result.users)

        if result.errors:
            for error in result.errors:
                self.stderr.write(self.style.ERROR(f"  ERROR: {error}"))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Bootstrap completed successfully."
            ))
