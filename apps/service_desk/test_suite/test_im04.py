"""
IM-04

Regression and feature coverage for Work Notes, Attachments,
and Requester Confirmation (ADR-010, Decision 3).

- Work notes are internal-only (Technician/Manager/Admin can add
  and see them; Requesters cannot add them and they are filtered
  from the history displayed to Requesters).
- Attachments are upload/download with extension and size
  validation, scoped through the RBAC ticket queryset.
- Requester Confirmation inserts an 'awaiting_confirmation'
  status between 'resolved' and 'closed'. Only the ticket's
  created_by user may close from that status.
"""

import io
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User, Group, Permission

from apps.service_desk.models import (
    Department,
    Ticket,
    TicketHistory,
    TicketAttachment,
)
from apps.service_desk.services.ticket_service import TicketService
from django.core.exceptions import ValidationError


class WorkNoteTests(TestCase):
    """Tests for the internal work notes feature."""

    def setUp(self):
        self.client = Client()

        technician_group = Group.objects.create(name="Technician")
        requester_group = Group.objects.create(name="Requester")

        view_ticket = Permission.objects.get(codename="view_ticket")
        change_ticket = Permission.objects.get(codename="change_ticket")

        technician_group.permissions.add(view_ticket, change_ticket)
        requester_group.permissions.add(view_ticket)

        self.technician = User.objects.create_user(
            username="im04_tech", password="pass123",
        )
        self.technician.groups.add(technician_group)

        self.requester = User.objects.create_user(
            username="im04_req", password="pass123",
        )
        self.requester.groups.add(requester_group)

        self.department = Department.objects.create(name="IM-04 Dept")
        self.ticket = Ticket.objects.create(
            title="IM-04 work note test",
            description="Testing work notes",
            status="open",
            created_by=self.requester,
            department=self.department,
        )
        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.technician,
        )

    def test_technician_can_add_work_note_via_service(self):
        entry = TicketService.add_work_note(
            self.ticket,
            "Internal investigation note",
            user=self.technician,
        )
        self.assertEqual(entry.event_type, TicketHistory.EVENT_WORK_NOTE)
        self.assertEqual(entry.comment, "Internal investigation note")
        self.assertEqual(entry.performed_by, self.technician)

    def test_empty_work_note_is_rejected(self):
        with self.assertRaises(ValidationError):
            TicketService.add_work_note(
                self.ticket, "   ", user=self.technician,
            )

    def test_technician_can_add_work_note_via_view(self):
        self.client.login(username="im04_tech", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/work-note/",
            {"work_note": "Checking the logs"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.ticket.history.filter(
                event_type=TicketHistory.EVENT_WORK_NOTE,
                comment="Checking the logs",
            ).exists()
        )

    def test_requester_cannot_add_work_note(self):
        """Requesters lack change_ticket — get 403."""
        self.client.login(username="im04_req", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/work-note/",
            {"work_note": "Should fail"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            self.ticket.history.filter(
                event_type=TicketHistory.EVENT_WORK_NOTE,
            ).exists()
        )

    def test_work_notes_visible_to_technician_on_detail_page(self):
        TicketService.add_work_note(
            self.ticket, "Internal finding", user=self.technician,
        )
        self.client.login(username="im04_tech", password="pass123")
        response = self.client.get(f"/tickets/{self.ticket.pk}/")
        self.assertContains(response, "Internal finding")
        self.assertContains(response, "Work Note Added")

    def test_work_notes_hidden_from_requester_on_detail_page(self):
        TicketService.add_work_note(
            self.ticket, "Secret internal note", user=self.technician,
        )
        self.client.login(username="im04_req", password="pass123")
        response = self.client.get(f"/tickets/{self.ticket.pk}/")
        # The work note content and event label should not appear
        self.assertNotContains(response, "Secret internal note")
        self.assertNotContains(response, "Work Note Added")

    def test_comments_still_visible_to_requester(self):
        """Ensure comment visibility is unchanged by work notes."""
        TicketService.add_comment(
            self.ticket, "Public comment", user=self.technician,
        )
        TicketService.add_work_note(
            self.ticket, "Private note", user=self.technician,
        )
        self.client.login(username="im04_req", password="pass123")
        response = self.client.get(f"/tickets/{self.ticket.pk}/")
        self.assertContains(response, "Public comment")
        self.assertNotContains(response, "Private note")


@override_settings(MEDIA_ROOT="/tmp/im04_test_media/")
class AttachmentTests(TestCase):
    """Tests for the ticket attachment feature."""

    def setUp(self):
        self.client = Client()

        technician_group = Group.objects.create(name="Technician")
        requester_group = Group.objects.create(name="Requester")

        view_ticket = Permission.objects.get(codename="view_ticket")
        change_ticket = Permission.objects.get(codename="change_ticket")

        technician_group.permissions.add(view_ticket, change_ticket)
        requester_group.permissions.add(view_ticket)

        self.technician = User.objects.create_user(
            username="im04_att_tech", password="pass123",
        )
        self.technician.groups.add(technician_group)

        self.requester = User.objects.create_user(
            username="im04_att_req", password="pass123",
        )
        self.requester.groups.add(requester_group)

        self.department = Department.objects.create(name="IM-04 Att Dept")
        self.ticket = Ticket.objects.create(
            title="IM-04 attachment test",
            description="Testing attachments",
            status="open",
            created_by=self.requester,
            department=self.department,
        )
        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.technician,
        )

    def _make_file(self, name="test.pdf", content=b"PDF content"):
        """Helper to create a Django-compatible uploaded file."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, content)

    def test_valid_pdf_attachment_via_service(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("report.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        attachment = TicketService.add_attachment(
            self.ticket, f, user=self.technician,
            description="Incident report",
        )
        self.assertEqual(attachment.ticket, self.ticket)
        self.assertEqual(attachment.uploaded_by, self.technician)
        self.assertEqual(attachment.original_filename, "report.pdf")
        self.assertEqual(attachment.description, "Incident report")

        # Audit trail
        self.assertTrue(
            self.ticket.history.filter(
                event_type=TicketHistory.EVENT_ATTACHMENT,
                comment__contains="report.pdf",
            ).exists()
        )

    def test_rejected_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")
        with self.assertRaises(ValidationError) as ctx:
            TicketService.add_attachment(
                self.ticket, f, user=self.technician,
            )
        self.assertIn(".exe", str(ctx.exception))

    def test_oversized_file_rejected(self):
        f = self._make_file("big.pdf", b"x")
        # Seek to end, report a size larger than the cap
        # We need to simulate a large file
        class FakeLargeFile:
            name = "big.pdf"
            def read(self, *a): return b""
            def seek(self, offset, whence=0): pass
            def tell(self): return TicketAttachment.MAX_FILE_SIZE_BYTES + 1

        with self.assertRaises(ValidationError) as ctx:
            TicketService.add_attachment(
                self.ticket, FakeLargeFile(), user=self.technician,
            )
        self.assertIn("exceeds", str(ctx.exception))

    def test_technician_can_upload_via_view(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("notes.txt", b"Some notes", content_type="text/plain")

        self.client.login(username="im04_att_tech", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/attach/",
            {"attachment": f, "description": "Investigation notes"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.attachments.count(), 1)
        att = self.ticket.attachments.first()
        self.assertEqual(att.original_filename, "notes.txt")
        self.assertEqual(att.description, "Investigation notes")

    def test_requester_cannot_upload_attachment(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("doc.pdf", b"PDF", content_type="application/pdf")

        self.client.login(username="im04_att_req", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/attach/",
            {"attachment": f},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.ticket.attachments.count(), 0)

    def test_requester_can_download_own_ticket_attachment(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("share.pdf", b"Shared doc", content_type="application/pdf")

        att = TicketService.add_attachment(
            self.ticket, f, user=self.technician,
        )

        self.client.login(username="im04_att_req", password="pass123")
        response = self.client.get(
            f"/tickets/{self.ticket.pk}/attachments/{att.pk}/",
        )
        self.assertEqual(response.status_code, 200)

    def test_no_file_selected_returns_error_message(self):
        self.client.login(username="im04_att_tech", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/attach/",
            {},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.attachments.count(), 0)

    def test_attachments_listed_on_detail_page(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("evlog.csv", b"a,b,c", content_type="text/csv")
        TicketService.add_attachment(
            self.ticket, f, user=self.technician, description="Event log",
        )
        self.client.login(username="im04_att_tech", password="pass123")
        response = self.client.get(f"/tickets/{self.ticket.pk}/")
        self.assertContains(response, "evlog.csv")
        self.assertContains(response, "Event log")


class RequesterConfirmationTests(TestCase):
    """Tests for the requester confirmation status flow."""

    def setUp(self):
        self.client = Client()

        technician_group = Group.objects.create(name="Technician")
        requester_group = Group.objects.create(name="Requester")

        view_ticket = Permission.objects.get(codename="view_ticket")
        change_ticket = Permission.objects.get(codename="change_ticket")

        technician_group.permissions.add(view_ticket, change_ticket)
        requester_group.permissions.add(view_ticket)

        self.technician = User.objects.create_user(
            username="im04_rc_tech", password="pass123",
        )
        self.technician.groups.add(technician_group)

        self.requester = User.objects.create_user(
            username="im04_rc_req", password="pass123",
        )
        self.requester.groups.add(requester_group)

        self.department = Department.objects.create(name="IM-04 RC Dept")
        self.ticket = Ticket.objects.create(
            title="IM-04 requester confirmation test",
            description="Testing the new confirmation flow",
            status="open",
            created_by=self.requester,
            department=self.department,
        )
        TicketService.assign_ticket(
            self.ticket, self.technician, user=self.technician,
        )
        TicketService.change_status(
            self.ticket, "in_progress", user=self.technician,
        )
        TicketService.change_status(
            self.ticket, "resolved", user=self.technician,
        )

    def test_resolved_to_awaiting_confirmation(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "awaiting_confirmation")

    def test_resolved_cannot_go_directly_to_closed(self):
        """resolved → closed is no longer valid (ADR-010, Decision 3)."""
        with self.assertRaises(ValidationError):
            TicketService.change_status(
                self.ticket, "closed", user=self.requester,
            )

    def test_requester_can_close_from_awaiting_confirmation(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        TicketService.close_ticket(self.ticket, user=self.requester)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "closed")

    def test_technician_cannot_close_from_awaiting_confirmation(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        with self.assertRaises(ValidationError) as ctx:
            TicketService.close_ticket(self.ticket, user=self.technician)
        self.assertIn("requester", str(ctx.exception).lower())
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "awaiting_confirmation")

    def test_close_from_awaiting_confirmation_records_confirmed_event(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        TicketService.close_ticket(self.ticket, user=self.requester)
        self.assertTrue(
            self.ticket.history.filter(
                event_type=TicketHistory.EVENT_CONFIRMED,
                from_status="awaiting_confirmation",
                to_status="closed",
            ).exists()
        )

    def test_request_confirmation_via_view(self):
        self.client.login(username="im04_rc_tech", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/request-confirmation/",
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "awaiting_confirmation")

    def test_requester_can_close_via_view(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        self.client.login(username="im04_rc_req", password="pass123")
        response = self.client.post(
            f"/tickets/{self.ticket.pk}/close/",
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "closed")

    def test_detail_page_shows_confirmation_button_for_requester(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        self.client.login(username="im04_rc_req", password="pass123")
        response = self.client.get(f"/tickets/{self.ticket.pk}/")
        self.assertContains(response, "Confirm &amp; Close")

    def test_detail_page_shows_awaiting_info_for_technician(self):
        TicketService.change_status(
            self.ticket, "awaiting_confirmation", user=self.technician,
        )
        self.client.login(username="im04_rc_tech", password="pass123")
        response = self.client.get(f"/tickets/{self.ticket.pk}/")
        self.assertContains(response, "Awaiting Confirmation")
        # Technician does NOT see the Confirm button (not the requester)
        self.assertNotContains(response, "Confirm &amp; Close")

    def test_close_ticket_rejects_non_awaiting_confirmation(self):
        """close_ticket() requires awaiting_confirmation, not resolved."""
        with self.assertRaises(ValidationError):
            TicketService.close_ticket(self.ticket, user=self.requester)
