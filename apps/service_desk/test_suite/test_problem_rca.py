"""
PM-04 — Problem RCA authoring workflows.

FiveWhys, FishboneFactor, Evidence, Action and Approval existed as
models and were rendered read-only: there was no service method and no
view that could create one. These tests pin the new service layer, the
state rules, the RBAC boundary and the detail-page surface.
"""

from datetime import date, timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from apps.service_desk.models import (
    Action,
    Approval,
    Department,
    Evidence,
    FishboneFactor,
    FiveWhys,
    Notification,
    Problem,
    RootCauseAnalysis,
)
from apps.service_desk.services.problem_service import ProblemService


class RCAServiceTests(TestCase):

    def setUp(self):
        self.it = Department.objects.create(name="IT")

        technician_group = Group.objects.create(name="Technician")
        technician_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_problem", "change_problem"]
            )
        )

        self.investigator = User.objects.create_user(
            username="rca-investigator", password="password123"
        )
        self.investigator.groups.add(technician_group)

        self.approver = User.objects.create_user(
            username="rca-approver", password="password123"
        )
        self.approver.groups.add(technician_group)

        self.problem = Problem.objects.create(
            title="Recurring database timeouts",
            description="Nightly job saturates the pool",
            department=self.it,
            assigned_to=self.investigator,
            created_by=self.investigator,
        )

    # ------------------------------------------------------------------
    # RCA lifecycle
    # ------------------------------------------------------------------

    def test_rca_is_created_on_first_use_and_reused_afterwards(self):
        first = ProblemService.get_or_create_rca(
            self.problem, user=self.investigator
        )
        second = ProblemService.get_or_create_rca(
            self.problem, user=self.investigator
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(RootCauseAnalysis.objects.count(), 1)

    def test_first_real_contribution_moves_the_rca_out_of_draft(self):
        rca = ProblemService.get_or_create_rca(self.problem)
        self.assertEqual(rca.status, "draft")

        ProblemService.add_five_whys_step(
            self.problem,
            question="Why did the pool saturate?",
            answer="The nightly job opens a connection per row.",
            user=self.investigator,
        )

        rca.refresh_from_db()
        self.assertEqual(rca.status, "in_progress")

    def test_update_rca_records_history(self):
        rca = ProblemService.get_or_create_rca(self.problem)

        ProblemService.update_rca(
            rca,
            user=self.investigator,
            method="fishbone",
            trigger_event="Batch window overlap",
        )

        rca.refresh_from_db()
        self.assertEqual(rca.method, "fishbone")
        self.assertTrue(
            self.problem.history.filter(
                comment__startswith="RCA updated"
            ).exists()
        )

    # ------------------------------------------------------------------
    # Five Whys
    # ------------------------------------------------------------------

    def test_step_numbers_are_allocated_by_the_service(self):
        for index in range(3):
            step = ProblemService.add_five_whys_step(
                self.problem,
                question=f"Why {index}?",
                answer=f"Because {index}",
                user=self.investigator,
            )

        self.assertEqual(step.step_number, 3)
        self.assertEqual(FiveWhys.objects.count(), 3)

    def test_empty_five_whys_content_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProblemService.add_five_whys_step(
                self.problem, question="  ", answer="x",
                user=self.investigator,
            )

        with self.assertRaises(ValidationError):
            ProblemService.add_five_whys_step(
                self.problem, question="x", answer="  ",
                user=self.investigator,
            )

    def test_duplicate_step_number_is_rejected(self):
        ProblemService.add_five_whys_step(
            self.problem, question="q", answer="a",
            user=self.investigator, step_number=1,
        )

        with self.assertRaises(ValidationError):
            ProblemService.add_five_whys_step(
                self.problem, question="q", answer="a",
                user=self.investigator, step_number=1,
            )

    # ------------------------------------------------------------------
    # Fishbone
    # ------------------------------------------------------------------

    def test_fishbone_factor_is_created_and_audited(self):
        factor = ProblemService.add_fishbone_factor(
            self.problem,
            category=FishboneFactor.CATEGORY_PROCESS,
            factor_description="No connection pooling in the batch job",
            user=self.investigator,
        )

        self.assertEqual(FishboneFactor.objects.count(), 1)
        self.assertTrue(
            self.problem.history.filter(
                comment__startswith="Fishbone factor added"
            ).exists()
        )
        self.assertFalse(factor.is_root_cause)

    def test_invalid_fishbone_category_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProblemService.add_fishbone_factor(
                self.problem,
                category="astrology",
                factor_description="x",
                user=self.investigator,
            )

    def test_factor_can_be_toggled_as_root_cause(self):
        factor = ProblemService.add_fishbone_factor(
            self.problem,
            category=FishboneFactor.CATEGORY_PROCESS,
            factor_description="x",
            user=self.investigator,
        )

        ProblemService.set_factor_as_root_cause(
            factor, user=self.investigator
        )
        factor.refresh_from_db()
        self.assertTrue(factor.is_root_cause)

        ProblemService.set_factor_as_root_cause(
            factor, user=self.investigator, is_root_cause=False
        )
        factor.refresh_from_db()
        self.assertFalse(factor.is_root_cause)

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def test_evidence_requires_a_title_and_a_reference(self):
        with self.assertRaises(ValidationError):
            ProblemService.add_evidence(
                self.problem, title=" ", file_or_link="http://x",
                user=self.investigator,
            )

        with self.assertRaises(ValidationError):
            ProblemService.add_evidence(
                self.problem, title="Log", file_or_link=" ",
                user=self.investigator,
            )

    def test_evidence_is_recorded(self):
        ProblemService.add_evidence(
            self.problem,
            title="Slow query log",
            file_or_link="https://logs.example.com/1",
            description="Captured during the incident window",
            user=self.investigator,
        )

        self.assertEqual(Evidence.objects.count(), 1)

    # ------------------------------------------------------------------
    # Actions (CAPA)
    # ------------------------------------------------------------------

    def test_action_is_raised_with_a_due_date(self):
        action = ProblemService.add_action(
            self.problem,
            action_type=Action.ACTION_TYPE_PREVENTIVE,
            description="Introduce connection pooling",
            due_date=date.today() + timedelta(days=7),
            assigned_to=self.investigator,
            user=self.investigator,
        )

        self.assertEqual(action.status, "open")
        self.assertEqual(Action.objects.count(), 1)

    def test_action_rejects_an_invalid_type_and_an_inactive_assignee(self):
        with self.assertRaises(ValidationError):
            ProblemService.add_action(
                self.problem,
                action_type="wishful",
                description="x",
                due_date=date.today(),
                user=self.investigator,
            )

        self.approver.is_active = False
        self.approver.save()

        with self.assertRaises(ValidationError):
            ProblemService.add_action(
                self.problem,
                action_type=Action.ACTION_TYPE_CORRECTIVE,
                description="x",
                due_date=date.today(),
                assigned_to=self.approver,
                user=self.investigator,
            )

    def test_action_status_transitions_are_validated(self):
        action = ProblemService.add_action(
            self.problem,
            action_type=Action.ACTION_TYPE_CORRECTIVE,
            description="x",
            due_date=date.today(),
            user=self.investigator,
        )

        # open -> completed is not a legal jump
        with self.assertRaises(ValidationError):
            ProblemService.change_action_status(
                action, "completed", user=self.investigator
            )

        ProblemService.change_action_status(
            action, "in_progress", user=self.investigator
        )
        ProblemService.change_action_status(
            action, "completed", user=self.investigator
        )
        action.refresh_from_db()
        self.assertEqual(action.status, "completed")

        # completed is terminal
        with self.assertRaises(ValidationError):
            ProblemService.change_action_status(
                action, "in_progress", user=self.investigator
            )

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def test_sign_off_requires_a_recorded_root_cause(self):
        with self.assertRaises(ValidationError):
            ProblemService.request_approval(
                self.problem, approver=self.approver,
                user=self.investigator,
            )

    def _ready_for_signoff(self):
        ProblemService.record_root_cause(
            self.problem,
            "Batch job opens one connection per row",
            user=self.investigator,
        )
        return ProblemService.request_approval(
            self.problem, approver=self.approver, user=self.investigator
        )

    def test_requesting_sign_off_completes_the_rca(self):
        approval = self._ready_for_signoff()

        self.assertEqual(approval.status, "pending")
        self.assertEqual(approval.rca.status, "completed")

    def test_duplicate_pending_request_for_the_same_approver_is_rejected(self):
        self._ready_for_signoff()

        with self.assertRaises(ValidationError):
            ProblemService.request_approval(
                self.problem, approver=self.approver,
                user=self.investigator,
            )

    def test_only_the_nominated_approver_may_decide(self):
        approval = self._ready_for_signoff()

        with self.assertRaises(ValidationError):
            ProblemService.decide_approval(
                approval, "approved", user=self.investigator
            )

    def test_a_decision_can_only_be_made_once(self):
        approval = self._ready_for_signoff()

        ProblemService.decide_approval(
            approval, "approved", user=self.approver, comments="Agreed"
        )

        with self.assertRaises(ValidationError):
            ProblemService.decide_approval(
                approval, "rejected", user=self.approver
            )

    def test_approval_locks_the_analysis(self):
        approval = self._ready_for_signoff()

        ProblemService.decide_approval(
            approval, "approved", user=self.approver
        )

        approval.rca.refresh_from_db()
        self.assertEqual(approval.rca.status, "approved")

        with self.assertRaises(ValidationError):
            ProblemService.add_five_whys_step(
                self.problem, question="q", answer="a",
                user=self.investigator,
            )

        with self.assertRaises(ValidationError):
            ProblemService.add_evidence(
                self.problem, title="t", file_or_link="l",
                user=self.investigator,
            )

    def test_approval_events_notify_the_problem_participants(self):
        approval = self._ready_for_signoff()

        ProblemService.decide_approval(
            approval, "approved", user=self.approver
        )

        self.assertTrue(
            Notification.objects.filter(
                kind=Notification.KIND_PROBLEM_UPDATE
            ).exists()
        )


class RCAViewTests(TestCase):
    """
    Every RCA action must be reachable through the Problem detail
    page, POST-only, CSRF-protected, and closed to anyone outside the
    problem's RBAC scope.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")
        self.hr = Department.objects.create(name="HR")

        technician_group = Group.objects.create(name="Technician")
        technician_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_problem", "change_problem"]
            )
        )

        requester_group = Group.objects.create(name="Requester")
        requester_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_ticket", "add_ticket"]
            )
        )

        self.investigator = User.objects.create_user(
            username="view-investigator", password="password123"
        )
        self.investigator.groups.add(technician_group)

        self.other_tech = User.objects.create_user(
            username="view-other-tech", password="password123"
        )
        self.other_tech.groups.add(technician_group)

        self.requester = User.objects.create_user(
            username="view-requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.problem = Problem.objects.create(
            title="Scoped problem",
            description="d",
            department=self.it,
            assigned_to=self.investigator,
            created_by=self.investigator,
        )

    def test_investigator_can_author_the_whole_rca_through_the_ui(self):
        self.client.login(
            username="view-investigator", password="password123"
        )

        base = f"/problems/{self.problem.pk}"

        response = self.client.post(
            f"{base}/rca/five-whys/",
            {"question": "Why?", "answer": "Because."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FiveWhys.objects.count(), 1)

        self.client.post(
            f"{base}/rca/fishbone/",
            {
                "category": FishboneFactor.CATEGORY_PROCESS,
                "factor_description": "Missing pooling",
            },
        )
        self.assertEqual(FishboneFactor.objects.count(), 1)

        self.client.post(
            f"{base}/rca/evidence/",
            {"title": "Log", "file_or_link": "https://x", "description": ""},
        )
        self.assertEqual(Evidence.objects.count(), 1)

        self.client.post(
            f"{base}/rca/actions/",
            {
                "action_type": Action.ACTION_TYPE_CORRECTIVE,
                "description": "Fix the job",
                "assigned_to": self.investigator.pk,
                "due_date": (date.today() + timedelta(days=3)).isoformat(),
            },
        )
        self.assertEqual(Action.objects.count(), 1)

    def test_detail_page_offers_to_start_an_analysis_when_none_exists(self):
        self.client.login(
            username="view-investigator", password="password123"
        )

        response = self.client.get(f"/problems/{self.problem.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start Root Cause Analysis")
        self.assertIsNone(response.context["rca"])

    def test_rca_panels_render_on_the_detail_page(self):
        ProblemService.get_or_create_rca(
            self.problem, user=self.investigator
        )

        self.client.login(
            username="view-investigator", password="password123"
        )

        response = self.client.get(f"/problems/{self.problem.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Five Whys")
        self.assertContains(response, "Corrective &amp; Preventive Actions")
        self.assertTrue(response.context["can_edit_rca"])

    def test_get_on_an_action_endpoint_is_not_allowed(self):
        self.client.login(
            username="view-investigator", password="password123"
        )

        response = self.client.get(
            f"/problems/{self.problem.pk}/rca/five-whys/"
        )
        self.assertEqual(response.status_code, 405)

    def test_requester_cannot_touch_rca_endpoints(self):
        self.client.login(username="view-requester", password="password123")

        response = self.client.post(
            f"/problems/{self.problem.pk}/rca/five-whys/",
            {"question": "q", "answer": "a"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FiveWhys.objects.count(), 0)

    def test_technician_cannot_author_on_an_unassigned_problem(self):
        self.client.login(username="view-other-tech", password="password123")

        response = self.client.post(
            f"/problems/{self.problem.pk}/rca/five-whys/",
            {"question": "q", "answer": "a"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(FiveWhys.objects.count(), 0)

    def test_anonymous_rca_post_redirects_to_login(self):
        response = self.client.post(
            f"/problems/{self.problem.pk}/rca/five-whys/",
            {"question": "q", "answer": "a"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_invalid_submission_reports_an_error_and_writes_nothing(self):
        self.client.login(
            username="view-investigator", password="password123"
        )

        response = self.client.post(
            f"/problems/{self.problem.pk}/rca/five-whys/",
            {"question": "", "answer": ""},
            follow=True,
        )

        self.assertEqual(FiveWhys.objects.count(), 0)
        self.assertTrue(
            any(m.level_tag == "error" for m in response.context["messages"])
        )

    def test_approval_flow_through_the_ui(self):
        self.client.login(
            username="view-investigator", password="password123"
        )

        ProblemService.record_root_cause(
            self.problem, "Because of X", user=self.investigator
        )

        self.client.post(
            f"/problems/{self.problem.pk}/rca/approvals/",
            {"approver": self.other_tech.pk},
        )

        approval = Approval.objects.get()
        self.assertEqual(approval.approver, self.other_tech)

        # The requester of the sign-off cannot approve their own work.
        response = self.client.post(
            f"/problems/{self.problem.pk}/rca/approvals/{approval.pk}/decide/",
            {"status": "approved", "comments": ""},
            follow=True,
        )
        approval.refresh_from_db()
        self.assertEqual(approval.status, "pending")

        # The nominated approver can — but only within their own scope,
        # so make them the assignee first.
        self.problem.assigned_to = self.other_tech
        self.problem.save()

        self.client.login(username="view-other-tech", password="password123")
        self.client.post(
            f"/problems/{self.problem.pk}/rca/approvals/{approval.pk}/decide/",
            {"status": "approved", "comments": "Looks right"},
        )

        approval.refresh_from_db()
        self.assertEqual(approval.status, "approved")


class ProblemStatisticsScopingTests(TestCase):
    """
    ProblemSelector.dashboard_statistics used to count every Problem in
    the table regardless of who was looking.
    """

    def setUp(self):
        self.client = Client()

        self.it = Department.objects.create(name="IT")
        self.hr = Department.objects.create(name="HR")

        technician_group = Group.objects.create(name="Technician")
        technician_group.permissions.set(
            Permission.objects.filter(
                codename__in=["view_problem", "change_problem"]
            )
        )

        self.technician = User.objects.create_user(
            username="stats-technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        Problem.objects.create(
            title="Mine",
            description="d",
            department=self.it,
            assigned_to=self.technician,
        )
        Problem.objects.create(
            title="Not mine",
            description="d",
            department=self.hr,
        )

    def test_problem_list_statistics_are_scoped_to_the_viewer(self):
        self.client.login(
            username="stats-technician", password="password123"
        )

        response = self.client.get("/problems/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total_problems"], 1)
        self.assertEqual(Problem.objects.count(), 2)
