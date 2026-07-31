from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.pam.models import AccessRequest, PrivilegedSession
from apps.pam.services import PAMService
from apps.service_desk.models import Company

User = get_user_model()


class PAMServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="PamCo", slug="pam-co")
        self.user = User.objects.create_user(username="eng1", password="pass12345")
        self.approver = User.objects.create_user(
            username="pamapprover", password="pass12345", is_staff=True
        )
        self.account = PAMService.register_account(
            self.company,
            name="Prod DB root",
            system="prod-postgres",
            username="root",
        )

    def test_request_approve_session(self):
        req = PAMService.request_access(
            self.account,
            self.user,
            justification="Emergency index rebuild",
            minutes=30,
            approver=self.approver,
        )
        self.assertEqual(req.state, AccessRequest.State.PENDING)
        PAMService.decide(req, approved=True, actor=self.approver, note="OK")
        req.refresh_from_db()
        self.assertEqual(req.state, AccessRequest.State.APPROVED)
        session = PAMService.start_session(req, client_ip="10.0.0.8")
        self.assertEqual(session.state, PrivilegedSession.State.ACTIVE)
        self.assertTrue(session.session_token)
        PAMService.end_session(session, note="done")
        session.refresh_from_db()
        self.assertEqual(session.state, PrivilegedSession.State.ENDED)
