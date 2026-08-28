"""
apps/service_desk/operations_views.py

Authenticated operational visibility for Administrators.

New flat view module rather than an addition to the existing
``views.py`` monolith — see ADR-011, Decision 2. Distinct from
reporting_views.py: this is infrastructure/operations status
(migrations, backups, scheduler health, email configuration), not
business data, and is gated to Administrators only rather than
self-gating per section like the Reports dashboard.

Read-only throughout: nothing here executes a backup, a migration,
or any other mutating operation — it only reports on state that
already exists (files on disk, migration graph, recent run logs).
"""

from pathlib import Path

import django
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.views.generic import TemplateView

from .models import SLARunLog
from .security.mixins import AdministratorRequiredMixin


class OperationsView(AdministratorRequiredMixin, TemplateView):
    template_name = "operations/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["generated_at"] = timezone.now()
        context["django_version"] = django.get_version()
        context["debug_mode"] = settings.DEBUG
        context["database_engine"] = connection.settings_dict.get(
            "ENGINE", "unknown"
        )
        context["email_notifications_enabled"] = getattr(
            settings, "SERVICE_DESK_EMAIL_NOTIFICATIONS", False
        )
        context["email_backend"] = getattr(settings, "EMAIL_BACKEND", "")

        context["pending_migrations"] = self._pending_migration_count()
        context["database_ready"] = self._database_ready()

        context["recent_sla_runs"] = SLARunLog.objects.all()[:10]
        context["recent_backups"] = self._recent_backups()

        return context

    @staticmethod
    def _pending_migration_count():
        from django.db.migrations.executor import MigrationExecutor

        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(
                executor.loader.graph.leaf_nodes()
            )
            return len(plan)
        except Exception:
            # A migration-status check must never break the ops page
            # itself — report "unknown" rather than raising.
            return None

    @staticmethod
    def _database_ready():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
            return bool(row and row[0] == 1)
        except Exception:
            return False

    @staticmethod
    def _recent_backups():
        backups_dir = Path(settings.BASE_DIR) / "backups"

        if not backups_dir.exists():
            return []

        files = sorted(
            backups_dir.glob("service_desk_backup_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:10]

        return [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "modified": timezone.datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.get_current_timezone()
                ),
            }
            for f in files
        ]
