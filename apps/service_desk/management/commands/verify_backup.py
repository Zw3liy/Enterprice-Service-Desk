"""
Restore-verify a backup produced by ``backup_database`` — proves the
file is actually restorable, not just present.

The restore happens into a brand-new, throwaway SQLite database file
inside a temporary directory that this command creates and deletes
itself; it never touches ``settings.DATABASES["default"]`` (whatever
that points to — SQLite in development, PostgreSQL in production) and
never modifies any existing database, table, row, or file outside
that temporary directory. This is what makes it safe to run against a
production backup from a developer's machine or CI without any risk
to the live deployment.
"""

import json
import tempfile
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):

    help = (
        "Restore a backup_database JSON backup into a disposable, "
        "throwaway SQLite database and report what was restored. "
        "Never touches the configured application database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            help="Path to a JSON backup produced by backup_database.",
        )

    def handle(self, *args, **options):
        backup_path = Path(options["backup_file"])

        if not backup_path.exists():
            raise CommandError(f"Backup file not found: {backup_path}")

        if backup_path.stat().st_size == 0:
            raise CommandError(f"Backup file is empty: {backup_path}")

        try:
            payload = backup_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"Backup file is not readable: {exc}") from exc

        try:
            records = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise CommandError(
                f"Backup file is not valid JSON: {exc}"
            ) from exc

        if not isinstance(records, list):
            raise CommandError(
                "Backup file does not contain a fixture list — expected "
                "a JSON array of serialized model records."
            )

        alias = "restore_verify"

        with tempfile.TemporaryDirectory(
            prefix="service_desk_restore_verify_"
        ) as tmp_dir:
            db_path = str(Path(tmp_dir) / "restore_verify.sqlite3")

            connections.databases[alias] = {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": db_path,
                "ATOMIC_REQUESTS": False,
                "AUTOCOMMIT": True,
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": False,
                "OPTIONS": {},
                "TIME_ZONE": None,
                "TEST": {},
            }

            try:
                call_command(
                    "migrate", database=alias, verbosity=0, interactive=False
                )

                try:
                    call_command(
                        "loaddata",
                        str(backup_path),
                        database=alias,
                        verbosity=0,
                    )
                except Exception as exc:
                    raise CommandError(
                        f"Backup did not restore cleanly: {exc}"
                    ) from exc

                from apps.service_desk.models import (
                    Change,
                    Ticket,
                )

                user_count = User.objects.using(alias).count()
                group_count = Group.objects.using(alias).count()
                ticket_count = Ticket.objects.using(alias).count()
                change_count = Change.objects.using(alias).count()

            finally:
                connections[alias].close()
                del connections.databases[alias]

        # handle()'s return value is written to stdout by Django's own
        # execute() when this runs as a real CLI invocation — it must
        # be a string (or None), never a dict, or that write crashes.
        # The counts are still available to a caller via call_command's
        # own return-value passthrough by parsing self.stdout, if ever
        # needed programmatically; kept simple here on purpose.
        self.stdout.write(
            self.style.SUCCESS(
                "Restore verification succeeded (disposable database, "
                "now discarded): "
                f"{user_count} user(s), {group_count} group(s), "
                f"{ticket_count} ticket(s), {change_count} change(s)."
            )
        )
