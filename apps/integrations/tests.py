from django.test import TestCase
from email.message import EmailMessage

from apps.integrations.email_inbound import EmailInboundService
from apps.integrations.ldap_sync import LDAPSyncService, LDAPUser
from apps.service_desk.models import Company


class EmailInboundTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="MailCo", slug="mail-co")

    def test_parse_and_ingest_new(self):
        msg = EmailMessage()
        msg["Subject"] = "Cannot print from finance floor"
        msg["From"] = "ava@example.com"
        msg["To"] = "helpdesk@example.com"
        msg["Message-ID"] = "<abc@example.com>"
        msg.set_content("The printer is offline since morning.")
        inbound = EmailInboundService.parse_message(msg)
        self.assertEqual(inbound.from_address, "ava@example.com")
        ticket = EmailInboundService.ingest(inbound, company=self.company)
        self.assertTrue(ticket.ticket_number)
        self.assertEqual(ticket.channel, "email")

    def test_ingest_updates_existing(self):
        first = EmailInboundService.ingest(
            EmailInboundService.parse_message(
                self._msg("VPN issue", "first body", "u@example.com")
            ),
            company=self.company,
        )
        follow = EmailInboundService.parse_message(
            self._msg(f"Re: [{first.ticket_number}] VPN issue", "still down", "u@example.com")
        )
        second = EmailInboundService.ingest(follow, company=self.company)
        self.assertEqual(first.pk, second.pk)
        self.assertGreaterEqual(second.comments.count(), 1)

    def _msg(self, subject, body, frm):
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = frm
        msg["To"] = "help@example.com"
        msg.set_content(body)
        return msg


class LDAPSyncTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="LdapCo", slug="ldap-co")

    def test_sync_creates_users(self):
        result = LDAPSyncService.sync_users(
            self.company,
            [
                LDAPUser(
                    username="jdoe",
                    email="jdoe@example.com",
                    first_name="Jane",
                    last_name="Doe",
                    is_agent=True,
                )
            ],
        )
        self.assertEqual(result["created"], 1)
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(username="jdoe")
        self.assertTrue(user.is_staff)
        self.assertTrue(hasattr(user, "agent_profile"))


class ConnectorRegistryTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="ConnCo", slug="conn-co")

    def test_upsert_and_test_slack(self):
        from apps.integrations.connectors import ConnectorRegistry
        from apps.integrations.models import IntegrationConnection

        conn = ConnectorRegistry.upsert(
            self.company,
            provider=IntegrationConnection.Provider.SLACK,
            name="IT Slack",
            config={"webhook_url": "https://hooks.example/slack"},
        )
        result = ConnectorRegistry.test_connection(conn)
        self.assertTrue(result["ok"])
        conn.refresh_from_db()
        self.assertEqual(conn.state, IntegrationConnection.State.ACTIVE)
