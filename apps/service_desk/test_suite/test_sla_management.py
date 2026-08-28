"""
SLA-01 — SLA and escalation management.

Covers deadline computation, warning/breach state, escalation
idempotency, the scheduled processing command, lifecycle hooks from
TicketService, policy RBAC and the scoped SLA dashboard.
"""

from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone
from io import StringIO

from apps.service_desk.models import (
    Department,
    SLAEscalation,
    SLAPolicy,
    SLARunLog,
    Ticket,
    TicketSLA,
)
from apps.service_desk.selectors.sla_selector import SLASelector
from apps.service_desk.services.sla_service import SLAService
from apps.service_desk.services.ticket_service import TicketService


class SLAPolicyModelTests(TestCase):

    def test_resolution_cannot_be_shorter_than_response(self):
        policy = SLAPolicy(
            name="Bad",
            priority="high",
            response_minutes=120,
            resolution_minutes=30,
        )

        with self.assertRaises(ValidationError):
            policy.full_clean()

    def test_warning_threshold_must_be_a_percentage(self):
        policy = SLAPolicy(
            name="Bad threshold",
            priority="high",
            response_minutes=10,
            resolution_minutes=60,
            warning_threshold_percent=140,
        )

        with self.assertRaises(ValidationError):
            policy.full_clean()

    def test_one_policy_per_priority_and_department(self):
        it = Department.objects.create(name="IT")

        SLAPolicy.objects.create(
            name="IT High",
            priority="high",
            department=it,
            response_minutes=15,
            resolution_minutes=240,
        )

        with self.assertRaises(Exception):
            SLAPolicy.objects.create(
                name="IT High duplicate",
                priority="high",
                department=it,
                response_minutes=30,
                resolution_minutes=480,
            )


class SLAServiceTests(TestCase):

    def setUp(self):
        self.it = Department.objects.create(name="IT")
        self.hr = Department.objects.create(name="HR")

        self.global_high = SLAPolicy.objects.create(
            name="Global High",
            priority="high",
            department=None,
            response_minutes=60,
            resolution_minutes=600,
        )

        self.it_high = SLAPolicy.objects.create(
            name="IT High",
            priority="high",
            department=self.it,
            response_minutes=15,
            resolution_minutes=120,
            warning_threshold_percent=50,
        )

        self.user = User.objects.create_user(
            username="sla-user", password="password123"
        )

    def _ticket(self, **kwargs):
        defaults = {
            "title": "T",
            "description": "d",
            "priority": "high",
            "department": self.it,
            "created_by": self.user,
        }
        defaults.update(kwargs)
        return Ticket.objects.create(**defaults)

    # -- policy resolution ------------------------------------------------

    def test_department_policy_beats_global_default(self):
        ticket = self._ticket()
        self.assertEqual(SLAService.resolve_policy(ticket), self.it_high)

    def test_falls_back_to_global_policy(self):
        ticket = self._ticket(department=self.hr)
        self.assertEqual(SLAService.resolve_policy(ticket), self.global_high)

    def test_inactive_policies_are_ignored(self):
        self.it_high.is_active = False
        self.it_high.save()

        ticket = self._ticket()
        self.assertEqual(SLAService.resolve_policy(ticket), self.global_high)

    def test_no_policy_configured_is_not_an_error(self):
        ticket = self._ticket(priority="low", department=self.hr)

        self.assertIsNone(SLAService.resolve_policy(ticket))
        self.assertIsNone(SLAService.attach_to_ticket(ticket))

    # -- attachment -------------------------------------------------------

    def test_attach_computes_deadlines_from_the_policy(self):
        now = timezone.now()
        ticket = self._ticket()

        record = SLAService.attach_to_ticket(ticket, now=now)

        self.assertEqual(record.policy, self.it_high)
        self.assertEqual(record.response_due_at, now + timedelta(minutes=15))
        self.assertEqual(
            record.resolution_due_at, now + timedelta(minutes=120)
        )

    def test_attach_is_idempotent(self):
        ticket = self._ticket()

        first = SLAService.attach_to_ticket(ticket)
        second = SLAService.attach_to_ticket(ticket)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(TicketSLA.objects.filter(ticket=ticket).count(), 1)

    def test_ticket_service_attaches_an_sla_on_creation(self):
        ticket = TicketService.create_ticket(
            title="Created through the service",
            description="d",
            priority="high",
            department=self.it,
            created_by=self.user,
        )

        self.assertTrue(TicketSLA.objects.filter(ticket=ticket).exists())

    # -- state ------------------------------------------------------------

    def test_states_progress_from_on_track_to_at_risk_to_breached(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket, now=now)

        # 50% threshold on a 15-minute response allowance
        self.assertEqual(
            record.response_state(now + timedelta(minutes=1)),
            TicketSLA.STATE_ON_TRACK,
        )
        self.assertEqual(
            record.response_state(now + timedelta(minutes=10)),
            TicketSLA.STATE_AT_RISK,
        )
        self.assertEqual(
            record.response_state(now + timedelta(minutes=20)),
            TicketSLA.STATE_BREACHED,
        )

    def test_overall_state_is_the_worst_of_the_two_clocks(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket, now=now)

        later = now + timedelta(minutes=20)

        self.assertEqual(
            record.resolution_state(later), TicketSLA.STATE_ON_TRACK
        )
        self.assertEqual(record.overall_state(later), TicketSLA.STATE_BREACHED)

    def test_first_response_inside_the_window_is_met(self):
        now = timezone.now()
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket, now=now)

        record = SLAService.mark_first_response(
            ticket, now=now + timedelta(minutes=5)
        )

        self.assertFalse(record.response_breached)
        self.assertEqual(record.response_state(), TicketSLA.STATE_MET)

    def test_late_first_response_is_recorded_as_breached(self):
        now = timezone.now()
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket, now=now)

        record = SLAService.mark_first_response(
            ticket, now=now + timedelta(minutes=30)
        )

        self.assertTrue(record.response_breached)

    def test_resolution_also_stops_an_unanswered_response_clock(self):
        now = timezone.now()
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket, now=now)

        record = SLAService.mark_resolved(
            ticket, now=now + timedelta(minutes=10)
        )

        self.assertIsNotNone(record.first_responded_at)
        self.assertIsNotNone(record.resolved_at)

    # -- lifecycle hooks --------------------------------------------------

    def test_status_change_to_in_progress_stops_the_response_clock(self):
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket)

        TicketService.change_status(ticket, "in_progress", user=self.user)

        record = TicketSLA.objects.get(ticket=ticket)
        self.assertIsNotNone(record.first_responded_at)

    def test_pending_pauses_the_clock(self):
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket)

        TicketService.change_status(ticket, "in_progress", user=self.user)
        TicketService.change_status(ticket, "pending", user=self.user)

        self.assertTrue(TicketSLA.objects.get(ticket=ticket).paused)

    def test_resolution_stops_the_resolution_clock(self):
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket)

        TicketService.change_status(ticket, "in_progress", user=self.user)
        TicketService.change_status(ticket, "resolved", user=self.user)

        self.assertIsNotNone(TicketSLA.objects.get(ticket=ticket).resolved_at)

    def test_work_note_stops_the_response_clock(self):
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket)

        TicketService.add_work_note(ticket, "Looking into it", user=self.user)

        self.assertIsNotNone(
            TicketSLA.objects.get(ticket=ticket).first_responded_at
        )

    def test_priority_change_recalculates_open_deadlines(self):
        SLAPolicy.objects.create(
            name="IT Urgent",
            priority="urgent",
            department=self.it,
            response_minutes=5,
            resolution_minutes=30,
        )

        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket)
        original_due = record.resolution_due_at

        TicketService.change_priority(ticket, "urgent", user=self.user)

        record.refresh_from_db()
        self.assertNotEqual(record.resolution_due_at, original_due)
        self.assertEqual(record.policy.name, "IT Urgent")

    def test_reopening_restarts_the_resolution_clock(self):
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket)

        TicketService.change_status(ticket, "in_progress", user=self.user)
        TicketService.change_status(ticket, "resolved", user=self.user)
        TicketService.change_status(
            ticket, "awaiting_confirmation", user=self.user
        )
        TicketService.change_status(ticket, "closed", user=ticket.created_by)
        TicketService.change_status(ticket, "open", user=self.user)

        record = TicketSLA.objects.get(ticket=ticket)
        self.assertIsNone(record.resolved_at)
        self.assertFalse(record.resolution_breached)

    # -- escalation -------------------------------------------------------

    def test_evaluate_raises_a_warning_then_a_breach(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket, now=now)

        created = SLAService.evaluate(record, now=now + timedelta(minutes=10))
        kinds = {e.kind for e in created}
        self.assertIn(SLAEscalation.KIND_RESPONSE_WARNING, kinds)

        created = SLAService.evaluate(record, now=now + timedelta(minutes=20))
        kinds = {e.kind for e in created}
        self.assertIn(SLAEscalation.KIND_RESPONSE_BREACH, kinds)

        record.refresh_from_db()
        self.assertTrue(record.response_breached)

    def test_evaluate_is_idempotent(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket, now=now)

        later = now + timedelta(hours=5)

        SLAService.evaluate(record, now=later)
        second_run = SLAService.evaluate(record, now=later)

        self.assertEqual(second_run, [])
        self.assertEqual(
            SLAEscalation.objects.filter(ticket_sla=record).count(), 2
        )

    def test_escalations_are_written_to_the_ticket_audit_trail(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket, now=now)

        SLAService.evaluate(record, now=now + timedelta(hours=5))

        self.assertTrue(
            ticket.history.filter(comment__startswith="SLA ").exists()
        )

    def test_paused_clocks_are_not_escalated(self):
        now = timezone.now()
        ticket = self._ticket()
        SLAService.attach_to_ticket(ticket, now=now)
        SLAService.set_paused(ticket, True)

        created = SLAService.process_due(now=now + timedelta(hours=5))

        self.assertEqual(created, [])

    def test_process_due_evaluates_every_live_clock(self):
        now = timezone.now()

        for index in range(3):
            ticket = self._ticket(title=f"T{index}")
            SLAService.attach_to_ticket(ticket, now=now)

        created = SLAService.process_due(now=now + timedelta(hours=5))

        # response breach + resolution breach for each of three tickets
        self.assertEqual(len(created), 6)

    def test_process_sla_command_runs_and_reports(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket)
        record.started_at = now - timedelta(hours=5)
        record.response_due_at = now - timedelta(hours=4)
        record.resolution_due_at = now - timedelta(hours=3)
        record.save()

        out = StringIO()
        call_command("process_sla", stdout=out)

        output = out.getvalue()
        self.assertIn("SLA processing complete", output)
        self.assertEqual(
            SLAEscalation.objects.filter(ticket_sla=record).count(), 2
        )

    def test_process_sla_dry_run_writes_nothing(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket)
        record.started_at = now - timedelta(hours=5)
        record.response_due_at = now - timedelta(hours=4)
        record.resolution_due_at = now - timedelta(hours=3)
        record.save()

        out = StringIO()
        call_command("process_sla", "--dry-run", stdout=out)

        self.assertIn("Dry run", out.getvalue())
        self.assertEqual(SLAEscalation.objects.count(), 0)

    def test_process_sla_writes_a_run_log(self):
        now = timezone.now()
        ticket = self._ticket()
        record = SLAService.attach_to_ticket(ticket)
        record.started_at = now - timedelta(hours=5)
        record.response_due_at = now - timedelta(hours=4)
        record.resolution_due_at = now - timedelta(hours=3)
        record.save()

        call_command("process_sla", stdout=StringIO())

        run = SLARunLog.objects.latest("started_at")
        self.assertTrue(run.succeeded)
        self.assertEqual(run.processed_count, 1)
        self.assertEqual(run.warnings_count, 0)
        self.assertEqual(run.breaches_count, 2)
        self.assertIsNotNone(run.finished_at)
        self.assertGreaterEqual(run.duration_seconds, 0)

    def test_process_sla_dry_run_does_not_write_a_run_log(self):
        call_command("process_sla", "--dry-run", stdout=StringIO())
        self.assertEqual(SLARunLog.objects.count(), 0)

    def test_process_sla_run_with_nothing_due_still_logs(self):
        call_command("process_sla", stdout=StringIO())
        run = SLARunLog.objects.latest("started_at")
        self.assertTrue(run.succeeded)
        self.assertEqual(run.processed_count, 0)

    def test_process_sla_failure_is_logged_and_reraised(self):
        from unittest.mock import patch

        with patch.object(
            SLAService, "process_due", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                call_command("process_sla", stdout=StringIO())

        run = SLARunLog.objects.latest("started_at")
        self.assertFalse(run.succeeded)
        self.assertIn("boom", run.error_message)
        self.assertIsNotNone(run.finished_at)


class SLAVisibilityTests(TestCase):
    """
    The SLA dashboard must never widen ticket visibility.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")
        self.hr = Department.objects.create(name="HR")

        SLAPolicy.objects.create(
            name="Global High",
            priority="high",
            response_minutes=15,
            resolution_minutes=120,
        )

        requester_group = Group.objects.create(name="Requester")
        requester_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_ticket", "add_ticket"]
            )
        )

        manager_group = Group.objects.create(name="Manager")
        manager_group.permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "view_ticket",
                    "change_ticket",
                    "view_slapolicy",
                    "add_slapolicy",
                    "change_slapolicy",
                ]
            )
        )

        self.requester = User.objects.create_user(
            username="sla-requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.other = User.objects.create_user(
            username="sla-other", password="password123"
        )
        self.other.groups.add(requester_group)

        self.manager = User.objects.create_user(
            username="sla-manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.it.managers.add(self.manager)

        self.admin = User.objects.create_superuser(
            username="sla-admin",
            password="password123",
            email="sla@example.com",
        )

        self.own = TicketService.create_ticket(
            title="Own high ticket",
            description="d",
            priority="high",
            department=self.it,
            created_by=self.requester,
        )

        self.foreign = TicketService.create_ticket(
            title="Foreign high ticket",
            description="d",
            priority="high",
            department=self.hr,
            created_by=self.other,
        )

    def test_dashboard_summary_is_scoped(self):
        from apps.service_desk.security.policies import get_ticket_queryset

        summary = SLASelector.dashboard_summary(
            get_ticket_queryset(self.requester)
        )
        self.assertEqual(summary["tracked"], 1)

        summary = SLASelector.dashboard_summary(
            get_ticket_queryset(self.admin)
        )
        self.assertEqual(summary["tracked"], 2)

    def test_sla_dashboard_view_shows_only_scoped_tickets(self):
        # Breach both clocks so both tickets appear in the breached list.
        for record in TicketSLA.objects.all():
            record.response_due_at = timezone.now() - timedelta(hours=2)
            record.resolution_due_at = timezone.now() - timedelta(hours=1)
            record.save()
            SLAService.evaluate(record)

        self.client.login(username="sla-requester", password="password123")
        response = self.client.get("/sla/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Own high ticket")
        self.assertNotContains(response, "Foreign high ticket")

    def test_anonymous_sla_dashboard_redirects_to_login(self):
        response = self.client.get("/sla/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_requester_does_not_see_scheduler_health_panel(self):
        SLARunLog.objects.create(
            started_at=timezone.now(), succeeded=True, processed_count=3
        )
        self.client.login(username="sla-requester", password="password123")
        response = self.client.get("/sla/")
        self.assertNotIn("recent_sla_runs", response.context)
        self.assertNotContains(response, "Scheduler Health")

    def test_manager_sees_scheduler_health_panel(self):
        SLARunLog.objects.create(
            started_at=timezone.now(), succeeded=True, processed_count=3
        )
        self.client.login(username="sla-manager", password="password123")
        response = self.client.get("/sla/")
        self.assertIn("recent_sla_runs", response.context)
        self.assertContains(response, "Scheduler Health")

    def test_requester_cannot_reach_policy_administration(self):
        self.client.login(username="sla-requester", password="password123")

        self.assertEqual(self.client.get("/sla/policies/").status_code, 403)
        self.assertEqual(
            self.client.get("/sla/policies/new/").status_code, 403
        )

    def test_manager_policy_list_is_scoped(self):
        SLAPolicy.objects.create(
            name="HR Low",
            priority="low",
            department=self.hr,
            response_minutes=60,
            resolution_minutes=600,
        )
        SLAPolicy.objects.create(
            name="IT Low",
            priority="low",
            department=self.it,
            response_minutes=60,
            resolution_minutes=600,
        )

        self.client.login(username="sla-manager", password="password123")
        response = self.client.get("/sla/policies/")

        names = {p.name for p in response.context["policies"]}
        self.assertIn("IT Low", names)
        self.assertIn("Global High", names)  # inherited default
        self.assertNotIn("HR Low", names)

    def test_manager_cannot_create_an_organisation_wide_policy(self):
        with self.assertRaises(ValidationError):
            SLAService.assert_policy_scope_allowed(self.manager, None)

    def test_manager_cannot_create_a_policy_for_another_department(self):
        with self.assertRaises(ValidationError):
            SLAService.assert_policy_scope_allowed(self.manager, self.hr)

    def test_administrator_may_create_any_policy(self):
        SLAService.assert_policy_scope_allowed(self.admin, None)
        SLAService.assert_policy_scope_allowed(self.admin, self.hr)

    def test_manager_creates_a_scoped_policy_through_the_view(self):
        self.client.login(username="sla-manager", password="password123")

        response = self.client.post(
            "/sla/policies/new/",
            {
                "name": "IT Medium",
                "priority": "medium",
                "department": self.it.pk,
                "response_minutes": 30,
                "resolution_minutes": 300,
                "warning_threshold_percent": 75,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SLAPolicy.objects.filter(name="IT Medium").exists())

    def test_main_dashboard_exposes_scoped_sla_indicators(self):
        self.client.login(username="sla-requester", password="password123")
        response = self.client.get("/")

        self.assertEqual(response.context["sla_summary"]["tracked"], 1)
