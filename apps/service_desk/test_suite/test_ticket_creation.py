"""
Ticket creation workflow — complete regression coverage.

Covers valid submissions across roles, required-field and choice
validation, inactive request types, tag normalisation, attachments,
CSRF, history/SLA side effects, RBAC bypass resistance and rollback.
"""

from __future__ import annotations

import io
from unittest import mock

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.service_desk.forms.ticket_forms import (
    normalize_tags,
    sanitize_attachment_filename,
)
from apps.service_desk.models import (
    Department,
    Notification,
    RequestType,
    SLAPolicy,
    Ticket,
    TicketAttachment,
    TicketHistory,
    TicketSLA,
)
from apps.service_desk.services.ticket_service import TicketService


@override_settings(MEDIA_ROOT="/tmp/ticket_creation_test_media/")
class TicketCreationWorkflowTests(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

        # Roles + permissions mirror create_roles.
        self.groups = {}
        for name in ("Requester", "Technician", "Manager", "Administrator"):
            self.groups[name] = Group.objects.create(name=name)

        perms = {
            codename: Permission.objects.get(codename=codename)
            for codename in (
                "view_ticket",
                "add_ticket",
                "change_ticket",
                "delete_ticket",
            )
        }
        self.groups["Requester"].permissions.set(
            [perms["view_ticket"], perms["add_ticket"]]
        )
        self.groups["Technician"].permissions.set(
            [perms["view_ticket"], perms["add_ticket"], perms["change_ticket"]]
        )
        self.groups["Manager"].permissions.set(
            [perms["view_ticket"], perms["add_ticket"], perms["change_ticket"]]
        )
        self.groups["Administrator"].permissions.set(list(perms.values()))

        self.requester = User.objects.create_user(
            username="create_req", password="pass123"
        )
        self.requester.groups.add(self.groups["Requester"])

        self.technician = User.objects.create_user(
            username="create_tech", password="pass123"
        )
        self.technician.groups.add(self.groups["Technician"])

        self.manager = User.objects.create_user(
            username="create_mgr", password="pass123"
        )
        self.manager.groups.add(self.groups["Manager"])

        self.admin = User.objects.create_user(
            username="create_admin", password="pass123", is_superuser=True
        )
        self.admin.groups.add(self.groups["Administrator"])

        self.it = Department.objects.create(name="Information Technology")
        self.hr = Department.objects.create(name="Human Resources")
        self.it.managers.add(self.manager)

        self.incident = RequestType.objects.create(
            name="Incident", description="Unplanned interruption", is_active=True
        )
        self.service_req = RequestType.objects.create(
            name="Service Request", is_active=True
        )
        self.inactive_type = RequestType.objects.create(
            name="Retired Type", is_active=False
        )

        self.sla = SLAPolicy.objects.create(
            name="Medium Priority Default",
            priority="medium",
            response_minutes=240,
            resolution_minutes=1440,
            is_active=True,
        )

        self.url = reverse("service_desk:ticket_create")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _login(self, user):
        assert self.client.login(username=user.username, password="pass123")

    def _csrf(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.cookies["csrftoken"].value

    def _post(self, data, files=None, follow=False):
        token = self._csrf()
        payload = {"csrfmiddlewaretoken": token, **data}
        if files:
            payload.update(files)
        return self.client.post(
            self.url,
            data=payload,
            follow=follow,
            HTTP_X_CSRFTOKEN=token,
        )

    def _valid_payload(self, **overrides):
        data = {
            "title": "Cannot connect to VPN",
            "description": "VPN client fails after the latest update.",
            "priority": "medium",
            "urgency": "high",
            "department": str(self.it.pk),
            "request_type": str(self.incident.pk),
            "tags": "VPN, Network, vpn",
        }
        data.update(overrides)
        return data

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_requester_can_create_ticket(self):
        self._login(self.requester)
        response = self._post(self._valid_payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ticket.objects.count(), 1)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.created_by, self.requester)
        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.request_type, self.incident)
        self.assertEqual(ticket.department, self.it)
        self.assertEqual(ticket.tags, "vpn,network")

    def test_technician_can_create_ticket(self):
        self._login(self.technician)
        response = self._post(self._valid_payload(title="Tech opened ticket"))
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.created_by, self.technician)

    def test_manager_can_create_ticket(self):
        self._login(self.manager)
        response = self._post(self._valid_payload(title="Manager opened ticket"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ticket.objects.get().created_by, self.manager)

    def test_admin_can_create_ticket(self):
        self._login(self.admin)
        response = self._post(self._valid_payload(title="Admin opened ticket"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ticket.objects.get().created_by, self.admin)

    def test_success_redirect_and_message(self):
        self._login(self.requester)
        response = self._post(self._valid_payload(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "created successfully")
        ticket = Ticket.objects.get()
        self.assertIn(
            reverse("service_desk:ticket_list"),
            response.redirect_chain[0][0],
        )
        self.assertIsNotNone(ticket.pk)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_required_fields_enforced(self):
        self._login(self.requester)
        response = self._post(
            {
                "title": "",
                "description": "",
                "priority": "medium",
                "urgency": "medium",
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertContains(response, "required", status_code=200)

    def test_invalid_priority_rejected(self):
        self._login(self.requester)
        response = self._post(self._valid_payload(priority="critical"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_invalid_urgency_rejected(self):
        self._login(self.requester)
        response = self._post(self._valid_payload(urgency="extreme"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_inactive_request_type_rejected(self):
        self._login(self.requester)
        response = self._post(
            self._valid_payload(request_type=str(self.inactive_type.pk))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_inactive_request_type_not_in_form_choices(self):
        self._login(self.requester)
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("Incident", content)
        self.assertNotIn("Retired Type", content)

    def test_short_title_and_description_rejected(self):
        self._login(self.requester)
        response = self._post(
            self._valid_payload(title="ab", description="too short")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_invalid_submission_retains_entered_values(self):
        self._login(self.requester)
        response = self._post(
            self._valid_payload(title="ab", description="long enough text here")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "long enough text here")

    def test_empty_master_data_shows_accessible_warning(self):
        RequestType.objects.all().delete()
        self._login(self.requester)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active request types")
        self.assertContains(response, "disabled")

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def test_tag_normalization_helper(self):
        self.assertEqual(
            normalize_tags("  VPN, Network, vpn;PRINTER  network "),
            "vpn,network,printer",
        )
        self.assertEqual(normalize_tags(""), "")

    def test_tags_normalised_on_create(self):
        self._login(self.requester)
        self._post(self._valid_payload(tags="Alpha, alpha, BETA beta"))
        self.assertEqual(Ticket.objects.get().tags, "alpha,beta")

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def test_valid_attachment_on_create(self):
        self._login(self.requester)
        upload = SimpleUploadedFile(
            "evidence.pdf", b"%PDF-1.4", content_type="application/pdf"
        )
        response = self._post(
            self._valid_payload(),
            files={"attachment": upload},
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.attachments.count(), 1)
        att = ticket.attachments.get()
        self.assertEqual(att.original_filename, "evidence.pdf")
        self.assertEqual(att.uploaded_by, self.requester)

    def test_oversized_attachment_rejected(self):
        self._login(self.requester)

        class FakeLarge:
            name = "big.pdf"
            size = TicketAttachment.MAX_FILE_SIZE_BYTES + 1

            def read(self, *a, **k):
                return b""

            def seek(self, *a, **k):
                return 0

            def tell(self):
                return self.size

            def chunks(self):
                yield b""

        response = self._post(
            self._valid_payload(),
            files={"attachment": FakeLarge()},
        )
        # Form validation rejects before create.
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_disallowed_extension_rejected(self):
        self._login(self.requester)
        upload = SimpleUploadedFile(
            "payload.exe", b"MZ", content_type="application/octet-stream"
        )
        response = self._post(
            self._valid_payload(),
            files={"attachment": upload},
        )
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_malicious_filename_sanitised(self):
        self.assertEqual(
            sanitize_attachment_filename("../../etc/passwd.pdf"),
            "passwd.pdf",
        )
        self.assertEqual(
            sanitize_attachment_filename("C:\\windows\\system32\\note.txt"),
            "note.txt",
        )

        self._login(self.technician)
        upload = SimpleUploadedFile(
            "../../etc/passwd.pdf", b"%PDF", content_type="application/pdf"
        )
        ticket = Ticket.objects.create(
            title="attach target",
            description="for filename sanitisation",
            created_by=self.technician,
            department=self.it,
        )
        att = TicketService.add_attachment(
            ticket, upload, user=self.technician
        )
        self.assertEqual(att.original_filename, "passwd.pdf")
        self.assertNotIn("..", att.original_filename)

    # ------------------------------------------------------------------
    # CSRF / RBAC bypass
    # ------------------------------------------------------------------

    def test_csrf_failure_rejects_post(self):
        self._login(self.requester)
        response = self.client.post(self.url, self._valid_payload())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_authenticated_without_permission_gets_403(self):
        bare = User.objects.create_user(username="bare", password="pass123")
        self.client.login(username="bare", password="pass123")
        # CSRF not required for the permission check path on GET.
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_client_cannot_force_owner_or_assignee(self):
        self._login(self.requester)
        response = self._post(
            self._valid_payload(
                created_by=str(self.admin.pk),
                assigned_to=str(self.technician.pk),
                status="closed",
            )
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.created_by, self.requester)
        self.assertIsNone(ticket.assigned_to)
        self.assertEqual(ticket.status, "open")

    def test_client_cannot_set_nonexistent_department_via_tamper(self):
        self._login(self.requester)
        response = self._post(self._valid_payload(department="999999"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    # ------------------------------------------------------------------
    # Side effects
    # ------------------------------------------------------------------

    def test_successful_creation_records_history(self):
        self._login(self.requester)
        self._post(self._valid_payload())
        ticket = Ticket.objects.get()
        self.assertTrue(
            ticket.history.filter(
                event_type=TicketHistory.EVENT_CREATED
            ).exists()
        )

    def test_sla_attached_on_create(self):
        self._login(self.requester)
        self._post(self._valid_payload(priority="medium"))
        ticket = Ticket.objects.get()
        self.assertTrue(TicketSLA.objects.filter(ticket=ticket).exists())
        self.assertEqual(ticket.sla.policy, self.sla)

    def test_notification_path_safe_on_create(self):
        """
        Creation itself does not notify the creator (actor == recipient).
        Assignment later does. Ensure the create path stays quiet.
        """
        self._login(self.requester)
        self._post(self._valid_payload())
        self.assertEqual(Notification.objects.count(), 0)

    def test_rollback_when_attachment_storage_fails(self):
        self._login(self.requester)
        upload = SimpleUploadedFile(
            "boom.pdf", b"%PDF", content_type="application/pdf"
        )

        with mock.patch(
            "apps.service_desk.services.ticket_service.TicketService.add_attachment",
            side_effect=ValidationError("disk full"),
        ):
            response = self._post(
                self._valid_payload(title="Should roll back"),
                files={"attachment": upload},
            )

        # create_ticket is @atomic and calls add_attachment in the same
        # block — a failure must leave no ticket behind.
        self.assertEqual(
            Ticket.objects.filter(title="Should roll back").count(), 0
        )
        self.assertEqual(response.status_code, 200)


class TicketCreateFormUnitTests(TestCase):
    """Direct form-level checks that do not need a full request cycle."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="form_user", password="pass123"
        )
        group = Group.objects.create(name="Requester")
        group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_ticket", "add_ticket"]
            )
        )
        self.user.groups.add(group)
        self.dept = Department.objects.create(name="Ops")
        self.rt = RequestType.objects.create(name="General Enquiry", is_active=True)

    def test_form_requires_request_type(self):
        from apps.service_desk.forms.ticket_forms import TicketCreateForm

        form = TicketCreateForm(
            data={
                "title": "Valid title here",
                "description": "A description long enough.",
                "priority": "low",
                "urgency": "low",
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("request_type", form.errors)
