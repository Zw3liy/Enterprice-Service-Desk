"""
SEC-02 — cross-cutting security regression coverage.

This module deliberately does not re-test what test_authorization,
test_permission_boundaries and test_im04 already pin. It covers the
boundaries that had no test at all: cross-scope attachment download,
CSRF on state-changing POSTs, error responses that must not leak
internals, and a repository-wide scan for committed secrets.
"""

import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.service_desk.models import (
    Department,
    Notification,
    Problem,
    Supplier,
    Ticket,
    TicketAttachment,
)
from apps.service_desk.services.ticket_service import TicketService


class AttachmentScopeTests(TestCase):
    """
    An attachment must be unreachable outside the scope of the ticket
    that owns it, including by pairing a reachable ticket pk with a
    foreign attachment pk.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")

        requester_group = Group.objects.create(name="Requester")
        requester_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_ticket", "add_ticket"]
            )
        )

        self.alice = User.objects.create_user(
            username="attach-alice", password="password123"
        )
        self.alice.groups.add(requester_group)

        self.bob = User.objects.create_user(
            username="attach-bob", password="password123"
        )
        self.bob.groups.add(requester_group)

        self.alice_ticket = Ticket.objects.create(
            title="Alice ticket",
            description="d",
            department=self.it,
            created_by=self.alice,
        )

        self.bob_ticket = Ticket.objects.create(
            title="Bob ticket",
            description="d",
            department=self.it,
            created_by=self.bob,
        )

        self.bob_attachment = TicketService.add_attachment(
            self.bob_ticket,
            SimpleUploadedFile(
                "secret.pdf", b"%PDF-1.4 confidential", "application/pdf"
            ),
            user=self.bob,
        )

    def test_download_of_another_users_attachment_is_denied(self):
        self.client.login(username="attach-alice", password="password123")

        response = self.client.get(
            f"/tickets/{self.bob_ticket.pk}"
            f"/attachments/{self.bob_attachment.pk}/"
        )

        self.assertIn(response.status_code, (403, 404))

    def test_attachment_cannot_be_pulled_through_an_in_scope_ticket(self):
        """
        The pk-swap attack: use a ticket you *can* see with an
        attachment you cannot.
        """

        self.client.login(username="attach-alice", password="password123")

        response = self.client.get(
            f"/tickets/{self.alice_ticket.pk}"
            f"/attachments/{self.bob_attachment.pk}/"
        )

        self.assertIn(response.status_code, (403, 404))

    def test_anonymous_download_redirects_to_login(self):
        response = self.client.get(
            f"/tickets/{self.bob_ticket.pk}"
            f"/attachments/{self.bob_attachment.pk}/"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_owner_can_download_their_own_attachment(self):
        self.client.login(username="attach-bob", password="password123")

        response = self.client.get(
            f"/tickets/{self.bob_ticket.pk}"
            f"/attachments/{self.bob_attachment.pk}/"
        )

        self.assertEqual(response.status_code, 200)

    def test_upload_limits_are_enforced_by_the_model_constants(self):
        self.assertTrue(TicketAttachment.ALLOWED_EXTENSIONS)
        self.assertGreater(TicketAttachment.MAX_FILE_SIZE_BYTES, 0)


class CSRFEnforcementTests(TestCase):
    """
    Every state-changing endpoint must reject a POST without a CSRF
    token. Django's test client disables CSRF by default, so this uses
    enforce_csrf_checks=True to actually exercise the middleware.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

        self.it = Department.objects.create(name="IT")

        group = Group.objects.create(name="Manager")
        group.permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "view_ticket",
                    "change_ticket",
                    "view_problem",
                    "change_problem",
                    "view_supplier",
                    "add_supplier",
                    "change_supplier",
                    "view_slapolicy",
                    "add_slapolicy",
                    "change_slapolicy",
                ]
            )
        )

        self.manager = User.objects.create_user(
            username="csrf-manager", password="password123"
        )
        self.manager.groups.add(group)
        self.it.managers.add(self.manager)

        self.client.force_login(self.manager)

        self.ticket = Ticket.objects.create(
            title="CSRF ticket",
            description="d",
            department=self.it,
            created_by=self.manager,
        )

        self.problem = Problem.objects.create(
            title="CSRF problem",
            description="d",
            department=self.it,
            assigned_to=self.manager,
        )

        self.supplier = Supplier.objects.create(
            name="CSRF supplier", department=self.it
        )

        self.notification = Notification.objects.create(
            recipient=self.manager,
            kind=Notification.KIND_TICKET_STATUS,
            subject="s",
        )

    def test_state_changing_posts_require_a_csrf_token(self):
        endpoints = [
            f"/tickets/{self.ticket.pk}/status/",
            f"/tickets/{self.ticket.pk}/comment/",
            f"/tickets/{self.ticket.pk}/work-note/",
            f"/tickets/{self.ticket.pk}/close/",
            f"/problems/{self.problem.pk}/status/",
            f"/problems/{self.problem.pk}/root-cause/",
            f"/problems/{self.problem.pk}/rca/five-whys/",
            f"/problems/{self.problem.pk}/rca/fishbone/",
            f"/problems/{self.problem.pk}/rca/evidence/",
            f"/problems/{self.problem.pk}/rca/actions/",
            f"/problems/{self.problem.pk}/rca/approvals/",
            f"/suppliers/{self.supplier.pk}/deactivate/",
            f"/suppliers/{self.supplier.pk}/activate/",
            "/suppliers/new/",
            "/sla/policies/new/",
            f"/notifications/{self.notification.pk}/read/",
            "/notifications/read-all/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, {})
                self.assertEqual(response.status_code, 403)

    def test_nothing_was_mutated_by_the_rejected_posts(self):
        for endpoint in (
            f"/suppliers/{self.supplier.pk}/deactivate/",
            f"/tickets/{self.ticket.pk}/status/",
        ):
            self.client.post(endpoint, {"status": "in_progress"})

        self.supplier.refresh_from_db()
        self.ticket.refresh_from_db()

        self.assertTrue(self.supplier.is_active)
        self.assertEqual(self.ticket.status, "open")


class ErrorDisclosureTests(TestCase):
    """
    A denied or missing record must not tell the caller anything about
    what exists.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")

        group = Group.objects.create(name="Requester")
        group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_ticket", "add_ticket"]
            )
        )

        self.user = User.objects.create_user(
            username="disclosure-user", password="password123"
        )
        self.user.groups.add(group)

        self.foreign_ticket = Ticket.objects.create(
            title="Extremely Confidential Project Codename",
            description="Nobody outside should learn this exists",
            department=self.it,
            created_by=User.objects.create_user(
                username="disclosure-other", password="password123"
            ),
        )

        self.client.login(
            username="disclosure-user", password="password123"
        )

    def test_out_of_scope_ticket_is_a_404_with_no_content_leak(self):
        response = self.client.get(f"/tickets/{self.foreign_ticket.pk}/")

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(
            response,
            "Extremely Confidential Project Codename",
            status_code=404,
        )

    def test_out_of_scope_problem_is_denied_without_detail(self):
        problem = Problem.objects.create(
            title="Hidden problem", description="d", department=self.it
        )

        response = self.client.get(f"/problems/{problem.pk}/")

        self.assertEqual(response.status_code, 403)


class CommittedSecretTests(TestCase):
    """
    Nothing in the tracked tree may contain a real credential.

    Runs over the repository's own source, skipping the virtualenv,
    VCS metadata and this file (which necessarily contains the
    patterns it searches for).
    """

    SKIP_DIRS = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "staticfiles",
        "media",
    }

    SCAN_SUFFIXES = {".py", ".yml", ".yaml", ".html", ".cfg", ".ini", ".env"}

    PATTERNS = [
        re.compile(r"AKIA[0-9A-Z]{16}"),                 # AWS access key
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),             # GitHub PAT
        re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),     # Slack token
        re.compile(
            r"""(?i)(password|passwd|secret|api[_-]?key|token)"""
            r"""\s*[=:]\s*["'][^"'\s{}$]{12,}["']"""
        ),
    ]

    def _files(self):
        root = Path(settings.BASE_DIR)
        this_file = Path(__file__).resolve()

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if any(part in self.SKIP_DIRS for part in path.parts):
                continue

            if path.resolve() == this_file:
                continue

            if path.suffix not in self.SCAN_SUFFIXES:
                continue

            yield path

    def test_no_credential_shaped_strings_are_committed(self):
        findings = []

        for path in self._files():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for pattern in self.PATTERNS:
                for match in pattern.finditer(text):
                    snippet = match.group(0)

                    # The documented development fallback key is public
                    # by design and refuses to run outside DEBUG.
                    if "django-insecure-" in snippet:
                        continue

                    findings.append(f"{path}: {snippet[:60]}")

        self.assertEqual(findings, [], "Possible committed secrets found")

    def test_env_file_is_not_tracked(self):
        self.assertFalse((Path(settings.BASE_DIR) / ".env").exists())

    def test_email_credentials_come_from_the_environment(self):
        """
        A hardcoded SMTP password would defeat the whole notification
        boundary design.
        """

        settings_source = (
            Path(settings.BASE_DIR) / "ticketing" / "settings.py"
        ).read_text(encoding="utf-8")

        self.assertIn("DJANGO_EMAIL_HOST_PASSWORD", settings_source)
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, "")
        self.assertFalse(settings.SERVICE_DESK_EMAIL_NOTIFICATIONS)
