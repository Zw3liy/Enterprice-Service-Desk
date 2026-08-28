"""
Timestamped, verified-non-empty application data backup.

Portable across SQLite (development) and PostgreSQL (production) —
this uses Django's own serialization framework (``dumpdata``) rather
than shelling out to a database-specific tool, so the same command
and the same restore-verification path
(``manage.py verify_backup``) work in every environment this project
runs in, including CI.

For a production PostgreSQL deployment, this JSON backup is a
portable *application-data* safety net; also take a native
``pg_dump`` for full-fidelity disaster recovery (sequences, indexes,
exact binary state) — see docs/operations/BACKUP_AND_RECOVERY.md for
both procedures side by side, and why the JSON format is what
``verify_backup`` restore-tests automatically.

``auth.permission`` and ``contenttypes`` are deliberately excluded —
both are regenerated deterministically by ``migrate`` and
``create_roles``, and restoring stale primary keys for them onto a
freshly migrated schema is a well-known source of ``loaddata``
integrity errors, not a real backup requirement.
"""

import io
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):

    help = (
        "Write a timestamped, verified-non-empty JSON backup of "
        "application data (users, groups, and everything in "
        "service_desk)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=None,
            help=(
                "Directory to write the backup into "
                "(default: BASE_DIR / 'backups')."
            ),
        )

    def handle(self, *args, **options):
        output_dir = Path(
            options["output_dir"] or (settings.BASE_DIR / "backups")
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = output_dir / f"service_desk_backup_{timestamp}.json"

        buffer = io.StringIO()
        try:
            call_command(
                "dumpdata",
                "auth.user",
                "auth.group",
                "service_desk",
                indent=2,
                stdout=buffer,
            )
        except Exception as exc:
            raise CommandError(f"dumpdata failed: {exc}") from exc

        payload = buffer.getvalue()

        if not payload.strip():
            raise CommandError(
                "dumpdata produced no output at all — refusing to write "
                "a backup file that would be empty. This indicates a "
                "serialization failure, not an empty database (an "
                "empty database still serializes to '[]')."
            )

        backup_path.write_text(payload, encoding="utf-8")

        size = backup_path.stat().st_size
        if size == 0:
            backup_path.unlink(missing_ok=True)
            raise CommandError(
                f"Backup file was written but is 0 bytes: {backup_path} "
                "— treat this backup as failed, not as an empty-but-valid "
                "backup."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backup written: {backup_path} ({size} bytes). "
                f"Verify it with: python manage.py verify_backup "
                f"{backup_path}"
            )
        )

        return str(backup_path)
