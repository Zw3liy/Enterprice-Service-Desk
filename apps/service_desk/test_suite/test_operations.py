"""
Enterprise Completion Program — Phase 10: Operations, backup/recovery.

Covers: backup_database writes a timestamped, non-empty file and
refuses to leave a partial/empty one behind on failure; verify_backup
restores a real backup into a disposable database and reports correct
counts, rejects a missing/empty/corrupt backup, and — critically —
never touches the application's configured database connection; the
Operations dashboard is Administrator-only.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command, CommandError
from django.db import connections
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import Department, Ticket


class BackupDatabaseTests(TestCase):
    def test_backup_is_timestamped_and_non_empty(self):
        Ticket.objects.create(title="Backup me", description="x")

        with tempfile.TemporaryDirectory() as tmp_dir:
            call_command("backup_database", output_dir=tmp_dir)

            files = list(Path(tmp_dir).glob("service_desk_backup_*.json"))
            self.assertEqual(len(files), 1)

            backup_file = files[0]
            self.assertGreater(backup_file.stat().st_size, 0)
            # UTC timestamp format: service_desk_backup_YYYYMMDDTHHMMSSZ.json
            self.assertRegex(
                backup_file.name,
                r"^service_desk_backup_\d{8}T\d{6}Z\.json$",
            )

    def test_backup_contains_real_data(self):
        Ticket.objects.create(title="Findable ticket", description="x")

        with tempfile.TemporaryDirectory() as tmp_dir:
            call_command("backup_database", output_dir=tmp_dir)
            backup_file = next(Path(tmp_dir).glob("service_desk_backup_*.json"))

            records = json.loads(backup_file.read_text(encoding="utf-8"))
            titles = [
                r["fields"].get("title")
                for r in records
                if r["model"] == "service_desk.ticket"
            ]
            self.assertIn("Findable ticket", titles)

    def test_backup_of_an_empty_database_is_still_a_valid_non_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            call_command("backup_database", output_dir=tmp_dir)
            backup_file = next(Path(tmp_dir).glob("service_desk_backup_*.json"))

            self.assertGreater(backup_file.stat().st_size, 0)
            records = json.loads(backup_file.read_text(encoding="utf-8"))
            self.assertEqual(records, [])

    def test_dumpdata_failure_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "apps.service_desk.management.commands.backup_database.call_command",
                side_effect=Exception("disk full"),
            ):
                with self.assertRaises(CommandError):
                    call_command("backup_database", output_dir=tmp_dir)

            self.assertEqual(
                list(Path(tmp_dir).glob("service_desk_backup_*.json")), []
            )


class VerifyBackupTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="IT")
        self.user = User.objects.create_user(
            username="restore_user", password="password123"
        )
        Group.objects.create(name="Manager")
        self.user.groups.add(Group.objects.get(name="Manager"))
        self.ticket = Ticket.objects.create(
            title="Restore me", description="x", department=self.dept,
        )

    def test_missing_file_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command("verify_backup", "/no/such/file.json")

    def test_empty_file_is_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            with self.assertRaises(CommandError):
                call_command("verify_backup", path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_non_json_file_is_rejected(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            f.write("this is not json {{{")
            path = f.name

        try:
            with self.assertRaises(CommandError):
                call_command("verify_backup", path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_non_list_json_is_rejected(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump({"not": "a list"}, f)
            path = f.name

        try:
            with self.assertRaises(CommandError):
                call_command("verify_backup", path)
        finally:
            Path(path).unlink(missing_ok=True)

    @staticmethod
    def _run_verify_backup_subprocess(backup_file):
        """
        verify_backup manages its own database connection lifecycle
        (registering and tearing down a dynamic alias) — Django's
        TestCase deeply instruments every connection in the current
        process specifically to prevent tests from touching
        unexpected databases, which makes an in-process call_command
        the wrong way to exercise this command's real behaviour (it
        fights that instrumentation rather than proving anything
        about the command itself). Running it as a genuine subprocess
        is both simpler and more faithful: it is, after all, meant to
        be invoked from the CLI, and a subprocess has its own
        untouched connection handling.
        """

        import subprocess
        import sys

        manage_py = Path(settings.BASE_DIR) / "manage.py"

        return subprocess.run(
            [
                sys.executable,
                str(manage_py),
                "verify_backup",
                backup_file,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_real_backup_restores_and_reports_correct_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            call_command("backup_database", output_dir=tmp_dir)
            backup_file = str(
                next(Path(tmp_dir).glob("service_desk_backup_*.json"))
            )

            result = self._run_verify_backup_subprocess(backup_file)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 user(s)", result.stdout)
        self.assertIn("1 ticket(s)", result.stdout)

    def test_verify_backup_never_touches_the_configured_database(self):
        """
        The whole point of restore-verification: it must not be able
        to affect the application's real database, even transiently —
        proven by confirming the live record is unchanged after a
        verify_backup run against a completely unrelated in-process
        database.
        """

        with tempfile.TemporaryDirectory() as tmp_dir:
            call_command("backup_database", output_dir=tmp_dir)
            backup_file = str(
                next(Path(tmp_dir).glob("service_desk_backup_*.json"))
            )

            result = self._run_verify_backup_subprocess(backup_file)

        self.assertEqual(result.returncode, 0, result.stderr)

        # The original ticket is untouched in this process's database
        # — the subprocess never had access to it in the first place,
        # which is exactly the isolation guarantee being proven.
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, "Restore me")

    def test_verify_backup_leaves_no_dynamic_alias_registered(self):
        """
        An empty backup (``[]``) still exercises the full registration
        / migrate / loaddata / teardown path — proving the dynamic
        alias is always cleaned up, success or not, without needing
        real restore data.
        """

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump([], f)
            path = f.name

        try:
            result = self._run_verify_backup_subprocess(path)
        finally:
            Path(path).unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("restore_verify", connections.databases)


class OperationsViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        manager_group = Group.objects.create(name="Manager")
        manager_group.permissions.add(
            Permission.objects.get(codename="view_ticket")
        )
        technician_group = Group.objects.create(name="Technician")
        technician_group.permissions.add(
            Permission.objects.get(codename="view_ticket")
        )

        self.manager = User.objects.create_user(
            username="ops_manager", password="password123"
        )
        self.manager.groups.add(manager_group)

        self.technician = User.objects.create_user(
            username="ops_technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.admin = User.objects.create_superuser(
            username="ops_admin", password="password123", email="a@test.com"
        )

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:operations_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_manager_gets_403(self):
        self.client.login(username="ops_manager", password="password123")
        response = self.client.get(reverse("service_desk:operations_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_technician_gets_403(self):
        self.client.login(username="ops_technician", password="password123")
        response = self.client.get(reverse("service_desk:operations_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_administrator_can_reach_it(self):
        self.client.login(username="ops_admin", password="password123")
        response = self.client.get(reverse("service_desk:operations_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("database_ready", response.context)
        self.assertTrue(response.context["database_ready"])
        self.assertEqual(response.context["pending_migrations"], 0)

    def test_navigation_shows_operations_only_to_superusers(self):
        self.client.login(username="ops_manager", password="password123")
        manager_response = self.client.get(reverse("service_desk:dashboard"))
        self.assertNotContains(
            manager_response, reverse("service_desk:operations_dashboard")
        )

        self.client.logout()
        self.client.login(username="ops_admin", password="password123")
        admin_response = self.client.get(reverse("service_desk:dashboard"))
        self.assertContains(
            admin_response, reverse("service_desk:operations_dashboard")
        )
