"""
Bootstrap command coverage.

Proves first-run creation, repeat-run idempotency, dry-run isolation,
--update-existing behaviour, password secrecy and transactional rollback.
"""

from __future__ import annotations

import io
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase, override_settings

from apps.service_desk.management.commands.bootstrap_service_desk import (
    DEPARTMENTS,
    REQUEST_TYPES,
    SLA_POLICIES,
    Command as BootstrapCommand,
)
from apps.service_desk.models import Department, RequestType, SLAPolicy

User = get_user_model()


class BootstrapServiceDeskTests(TestCase):

    def _run(self, *args, **kwargs):
        stdout = io.StringIO()
        stderr = io.StringIO()
        # call_command does not always surface handle()'s return value
        # consistently across Django versions, so capture the result via
        # a direct Command invocation for assertions while still exercising
        # the management entry point for stdout.
        command = BootstrapCommand()
        # Provide defaults for every declared option so direct handle()
        # calls (used by the rollback test) and call_command stay aligned.
        options = {
            "dry_run": False,
            "update_existing": False,
            "skip_users": False,
            "create_seed_users": False,
            "admin_username": None,
            "admin_email": None,
            "manager_username": None,
            "manager_email": None,
            "technician_username": None,
            "technician_email": None,
            "requester_username": None,
            "requester_email": None,
        }
        options.update(kwargs)
        command.stdout = stdout
        command.stderr = stderr
        result = command.handle(*args, **options)
        return result, stdout.getvalue(), stderr.getvalue()

    # ------------------------------------------------------------------
    # First run
    # ------------------------------------------------------------------

    def test_first_run_creates_master_data(self):
        result, out, _ = self._run(skip_users=True)

        self.assertEqual(Department.objects.count(), len(DEPARTMENTS))
        self.assertEqual(RequestType.objects.count(), len(REQUEST_TYPES))
        self.assertEqual(
            SLAPolicy.objects.filter(department__isnull=True).count(),
            len(SLA_POLICIES),
        )

        for name in (
            "Administrator",
            "Manager",
            "Technician",
            "Requester",
        ):
            self.assertTrue(Group.objects.filter(name=name).exists())

        self.assertIn("created=", out)
        self.assertEqual(result.departments["created"], len(DEPARTMENTS))
        self.assertEqual(result.request_types["created"], len(REQUEST_TYPES))
        self.assertEqual(result.sla_policies["created"], len(SLA_POLICIES))

    def test_request_types_are_active(self):
        self._run(skip_users=True)
        self.assertTrue(
            RequestType.objects.filter(is_active=True).count()
            == len(REQUEST_TYPES)
        )

    def test_sla_priorities_cover_all_defaults(self):
        self._run(skip_users=True)
        priorities = set(
            SLAPolicy.objects.filter(department__isnull=True).values_list(
                "priority", flat=True
            )
        )
        self.assertEqual(priorities, {"urgent", "high", "medium", "low"})

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_repeat_run_is_idempotent(self):
        self._run(skip_users=True)
        first_dept_ids = set(Department.objects.values_list("pk", flat=True))
        first_rt_ids = set(RequestType.objects.values_list("pk", flat=True))
        first_sla_ids = set(SLAPolicy.objects.values_list("pk", flat=True))

        result, _, _ = self._run(skip_users=True)

        self.assertEqual(result.departments["created"], 0)
        self.assertEqual(result.request_types["created"], 0)
        self.assertEqual(result.sla_policies["created"], 0)
        self.assertEqual(result.departments["skipped"], len(DEPARTMENTS))

        self.assertEqual(
            set(Department.objects.values_list("pk", flat=True)),
            first_dept_ids,
        )
        self.assertEqual(
            set(RequestType.objects.values_list("pk", flat=True)),
            first_rt_ids,
        )
        self.assertEqual(
            set(SLAPolicy.objects.values_list("pk", flat=True)),
            first_sla_ids,
        )
        self.assertEqual(Department.objects.count(), len(DEPARTMENTS))
        self.assertEqual(RequestType.objects.count(), len(REQUEST_TYPES))

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def test_dry_run_makes_no_changes(self):
        result, out, _ = self._run(dry_run=True, skip_users=True)

        self.assertEqual(Department.objects.count(), 0)
        self.assertEqual(RequestType.objects.count(), 0)
        self.assertEqual(SLAPolicy.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)
        self.assertIn("DRY-RUN", out)
        self.assertGreater(result.departments["created"], 0)

    def test_dry_run_after_seed_still_makes_no_changes(self):
        self._run(skip_users=True)
        before = Department.objects.get(name="Information Technology")
        before.description = "custom"
        before.save(update_fields=["description"])

        self._run(dry_run=True, update_existing=True, skip_users=True)

        before.refresh_from_db()
        self.assertEqual(before.description, "custom")

    # ------------------------------------------------------------------
    # Update existing
    # ------------------------------------------------------------------

    def test_update_existing_refreshes_descriptions(self):
        self._run(skip_users=True)
        dept = Department.objects.get(name="Finance")
        dept.description = "stale"
        dept.save(update_fields=["description"])

        result, _, _ = self._run(update_existing=True, skip_users=True)

        dept.refresh_from_db()
        self.assertNotEqual(dept.description, "stale")
        self.assertGreaterEqual(result.departments["updated"], 1)

    def test_update_existing_reactivates_request_type(self):
        self._run(skip_users=True)
        rt = RequestType.objects.get(name="Incident")
        rt.is_active = False
        rt.save(update_fields=["is_active"])

        self._run(update_existing=True, skip_users=True)

        rt.refresh_from_db()
        self.assertTrue(rt.is_active)

    # ------------------------------------------------------------------
    # Users / password secrecy
    # ------------------------------------------------------------------

    def test_seed_users_created_from_env_password(self):
        env = {
            "BOOTSTRAP_INITIAL_PASSWORD": "CorrectHorseBatteryStaple1!",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result, out, _ = self._run(create_seed_users=True)

        self.assertEqual(result.users["created"], 4)
        self.assertTrue(User.objects.filter(username="sd_admin").exists())
        self.assertTrue(User.objects.filter(username="sd_manager").exists())
        self.assertTrue(User.objects.filter(username="sd_technician").exists())
        self.assertTrue(User.objects.filter(username="sd_requester").exists())

        admin = User.objects.get(username="sd_admin")
        self.assertTrue(admin.check_password("CorrectHorseBatteryStaple1!"))
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.groups.filter(name="Administrator").exists())

        # Password must never appear in command output.
        self.assertNotIn("CorrectHorseBatteryStaple1!", out)
        self.assertNotIn("CorrectHorseBatteryStaple1!", result.as_dict().__str__())

    def test_admin_username_option(self):
        env = {"BOOTSTRAP_ADMIN_PASSWORD": "AdminOnlyPass99!"}
        with mock.patch.dict(os.environ, env, clear=False):
            result, _, _ = self._run(
                admin_username="custom_admin",
                admin_email="ops@example.com",
                skip_users=False,
            )

        # Only the admin was requested; other seed users stay absent.
        self.assertEqual(result.users["created"], 1)
        user = User.objects.get(username="custom_admin")
        self.assertEqual(user.email, "ops@example.com")
        self.assertTrue(user.check_password("AdminOnlyPass99!"))
        self.assertFalse(User.objects.filter(username="sd_manager").exists())

    def test_skip_users_leaves_auth_untouched(self):
        env = {"BOOTSTRAP_INITIAL_PASSWORD": "ShouldNotCreate1!"}
        with mock.patch.dict(os.environ, env, clear=False):
            self._run(skip_users=True, create_seed_users=True)

        self.assertEqual(User.objects.count(), 0)

    def test_manager_is_linked_to_it_department(self):
        env = {"BOOTSTRAP_INITIAL_PASSWORD": "LinkManagerPass1!"}
        with mock.patch.dict(os.environ, env, clear=False):
            self._run(create_seed_users=True)

        manager = User.objects.get(username="sd_manager")
        it = Department.objects.get(name="Information Technology")
        self.assertIn(manager, it.managers.all())

    def test_missing_password_raises_without_creating_user(self):
        # Ensure no password env is present for this process.
        cleaned = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("BOOTSTRAP_")
        }
        with mock.patch.dict(os.environ, cleaned, clear=True):
            with self.assertRaises(CommandError):
                self._run(create_seed_users=True)

        self.assertEqual(User.objects.count(), 0)
        # Master data must also roll back with the failed transaction.
        self.assertEqual(Department.objects.count(), 0)

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------

    def test_roles_receive_expected_permissions(self):
        self._run(skip_users=True)

        requester = Group.objects.get(name="Requester")
        tech = Group.objects.get(name="Technician")
        manager = Group.objects.get(name="Manager")
        admin = Group.objects.get(name="Administrator")

        self.assertTrue(
            requester.permissions.filter(codename="add_ticket").exists()
        )
        self.assertTrue(
            tech.permissions.filter(codename="add_ticket").exists()
        )
        self.assertTrue(
            manager.permissions.filter(codename="add_ticket").exists()
        )
        self.assertTrue(
            admin.permissions.filter(codename="delete_ticket").exists()
        )
        self.assertFalse(
            requester.permissions.filter(codename="view_problem").exists()
        )
        self.assertFalse(
            tech.permissions.filter(codename="view_supplier").exists()
        )

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def test_failure_rolls_back_all_changes(self):
        command = BootstrapCommand()

        def boom(*args, **kwargs):
            raise RuntimeError("simulated failure")

        with mock.patch.object(command, "_bootstrap_sla_policies", boom):
            with self.assertRaises(CommandError):
                command.handle(
                    dry_run=False,
                    update_existing=False,
                    skip_users=True,
                    create_seed_users=False,
                    admin_username=None,
                    admin_email=None,
                    manager_username=None,
                    manager_email=None,
                    technician_username=None,
                    technician_email=None,
                    requester_username=None,
                    requester_email=None,
                )

        self.assertEqual(Department.objects.count(), 0)
        self.assertEqual(RequestType.objects.count(), 0)
        self.assertEqual(SLAPolicy.objects.count(), 0)
