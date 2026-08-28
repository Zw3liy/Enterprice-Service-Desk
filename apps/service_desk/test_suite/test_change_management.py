"""
Enterprise Completion Program — Phase 3: Change Management.

Covers: risk calculation, illegal-transition rejection, schedule
conflict detection, separation of duties (an approver may be neither
the requester nor the assigned implementer), RBAC scoping (Requester
excluded entirely, mirroring ADR-010's Problem Management precedent),
cross-scope 404, anonymous redirect, POST-only/CSRF, and the full
lifecycle through real views including a failure/rollback path.
"""

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.service_desk.models import Change, ChangeApproval, ChangeHistory, Department
from apps.service_desk.security.policies import get_change_queryset
from apps.service_desk.services.change_service import ChangeService


def _grant(group, *codenames):
    group.permissions.add(
        *Permission.objects.filter(codename__in=codenames)
    )


class ChangeServiceTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="IT")

        self.requester = User.objects.create_user(
            username="chg_requester", password="password123"
        )
        self.manager = User.objects.create_user(
            username="chg_manager", password="password123"
        )
        Group.objects.create(name="Manager")
        self.manager.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.manager)

        self.other_manager = User.objects.create_user(
            username="chg_other_manager", password="password123"
        )
        self.other_manager.groups.add(Group.objects.get(name="Manager"))

        self.implementer = User.objects.create_user(
            username="chg_implementer", password="password123"
        )

    def _new_change(self, **overrides):
        data = {
            "title": "Upgrade router firmware",
            "description": "x",
            "department": self.dept,
        }
        data.update(overrides)
        return ChangeService.create_change(self.requester, **data)

    def test_risk_is_calculated_from_impact_and_urgency(self):
        change = self._new_change()
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="high", urgency="high"
        )
        change.refresh_from_db()
        self.assertEqual(change.risk_level, Change.RISK_CRITICAL)

    def test_illegal_transition_is_rejected(self):
        change = self._new_change()
        # draft -> approved is not a legal edge
        with self.assertRaises(ValidationError):
            ChangeService.approve_change(change, self.manager)

    def test_assess_requires_submitted_status(self):
        change = self._new_change()
        with self.assertRaises(ValidationError):
            ChangeService.assess_change(
                change, self.manager, impact="low", urgency="low"
            )

    def test_technician_cannot_approve(self):
        change = self._new_change()
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        with self.assertRaises(ValidationError):
            ChangeService.approve_change(change, self.implementer)

    def test_requester_cannot_approve_own_change(self):
        change = self._new_change()
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        # requester happens to also be given manager role for this check
        self.requester.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.requester)

        with self.assertRaises(ValidationError):
            ChangeService.approve_change(change, self.requester)

    def test_assigned_implementer_cannot_approve_own_implementation(self):
        change = self._new_change()
        ChangeService.assign_change(change, self.implementer, user=self.manager)
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )

        self.implementer.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.implementer)

        with self.assertRaises(ValidationError):
            ChangeService.approve_change(change, self.implementer)

    def test_reject_requires_a_comment(self):
        change = self._new_change()
        ChangeService.submit_change(change, user=self.requester)
        with self.assertRaises(ValidationError):
            ChangeService.reject_change(change, self.manager, "")

    def test_reject_records_history_and_approval(self):
        change = self._new_change()
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.reject_change(change, self.manager, "Too risky.")
        change.refresh_from_db()

        self.assertEqual(change.status, Change.STATUS_REJECTED)
        self.assertTrue(
            change.approvals.filter(
                decision=ChangeApproval.DECISION_REJECTED
            ).exists()
        )
        self.assertTrue(
            change.history.filter(
                event_type=ChangeHistory.EVENT_REJECTED
            ).exists()
        )

    def test_schedule_requires_approved_status(self):
        change = self._new_change()
        now = timezone.now()
        with self.assertRaises(ValidationError):
            ChangeService.schedule_change(
                change, self.manager, now, now + timedelta(hours=1)
            )

    def test_schedule_rejects_start_after_end(self):
        change = self._new_change()
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(change, self.manager)

        now = timezone.now()
        with self.assertRaises(ValidationError):
            ChangeService.schedule_change(
                change, self.manager, now, now - timedelta(hours=1)
            )

    def test_conflicting_schedule_is_rejected(self):
        existing = self._new_change(title="Existing maintenance window")
        ChangeService.submit_change(existing, user=self.requester)
        ChangeService.assess_change(
            existing, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(existing, self.manager)

        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        ChangeService.schedule_change(existing, self.manager, start, end)

        conflicting = self._new_change(title="Conflicting change")
        ChangeService.submit_change(conflicting, user=self.requester)
        ChangeService.assess_change(
            conflicting, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(conflicting, self.manager)

        overlap_start = start + timedelta(minutes=30)
        overlap_end = overlap_start + timedelta(hours=1)

        with self.assertRaises(ValidationError):
            ChangeService.schedule_change(
                conflicting, self.manager, overlap_start, overlap_end
            )

    def test_non_overlapping_schedule_in_same_department_is_allowed(self):
        existing = self._new_change(title="Existing maintenance window")
        ChangeService.submit_change(existing, user=self.requester)
        ChangeService.assess_change(
            existing, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(existing, self.manager)

        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)
        ChangeService.schedule_change(existing, self.manager, start, end)

        later = self._new_change(title="Later change")
        ChangeService.submit_change(later, user=self.requester)
        ChangeService.assess_change(
            later, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(later, self.manager)

        later_start = end + timedelta(hours=1)
        later_end = later_start + timedelta(hours=1)

        ChangeService.schedule_change(later, self.manager, later_start, later_end)
        later.refresh_from_db()
        self.assertEqual(later.status, Change.STATUS_SCHEDULED)

    def test_only_implementer_manager_or_admin_may_advance_implementation(self):
        change = self._new_change()
        ChangeService.assign_change(change, self.implementer, user=self.manager)
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(change, self.manager)
        ChangeService.schedule_change(
            change,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )

        bystander = User.objects.create_user(
            username="chg_bystander", password="password123"
        )
        with self.assertRaises(ValidationError):
            ChangeService.start_implementation(change, user=bystander)

        ChangeService.start_implementation(change, user=self.implementer)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_IMPLEMENTING)

    def test_fail_requires_a_reason(self):
        change = self._new_change()
        ChangeService.assign_change(change, self.implementer, user=self.manager)
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(change, self.manager)
        ChangeService.schedule_change(
            change,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )
        ChangeService.start_implementation(change, user=self.implementer)

        with self.assertRaises(ValidationError):
            ChangeService.fail_change(change, self.implementer, "")

    def test_full_success_and_failure_paths(self):
        # success path
        change = self._new_change()
        ChangeService.assign_change(change, self.implementer, user=self.manager)
        ChangeService.submit_change(change, user=self.requester)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(change, self.manager)
        ChangeService.schedule_change(
            change,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )
        ChangeService.start_implementation(change, user=self.implementer)
        ChangeService.request_validation(change, user=self.implementer)
        ChangeService.complete_change(change, user=self.implementer)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_COMPLETED)
        self.assertFalse(change.is_open)

        # failure + rollback path
        failing = self._new_change(title="Failing change")
        ChangeService.assign_change(failing, self.implementer, user=self.manager)
        ChangeService.submit_change(failing, user=self.requester)
        ChangeService.assess_change(
            failing, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(failing, self.manager)
        ChangeService.schedule_change(
            failing,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )
        ChangeService.start_implementation(failing, user=self.implementer)
        ChangeService.fail_change(
            failing, self.implementer, "Deployment broke connectivity."
        )
        ChangeService.rollback_change(
            failing, self.implementer, "Reverted to prior firmware."
        )
        failing.refresh_from_db()
        self.assertEqual(failing.status, Change.STATUS_ROLLED_BACK)
        self.assertFalse(failing.is_open)


class ChangeVisibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="IT")
        self.other_dept = Department.objects.create(name="Finance")

        requester_group = Group.objects.create(name="Requester")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_change", "add_change", "change_change")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_change", "change_change")

        self.requester = User.objects.create_user(
            username="vis_chg_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.technician = User.objects.create_user(
            username="vis_chg_technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.other_technician = User.objects.create_user(
            username="vis_chg_other_technician", password="password123"
        )
        self.other_technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="vis_chg_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.other_manager = User.objects.create_user(
            username="vis_chg_other_manager", password="password123"
        )
        self.other_manager.groups.add(manager_group)
        self.other_dept.managers.add(self.other_manager)

        self.admin = User.objects.create_superuser(
            username="vis_chg_admin", password="password123", email="a@test.com"
        )

        self.change = ChangeService.create_change(
            self.requester,
            title="Router upgrade",
            description="x",
            department=self.dept,
        )
        ChangeService.assign_change(
            self.change, self.technician, user=self.manager
        )

    def test_anonymous_sees_nothing(self):
        self.assertEqual(
            get_change_queryset(AnonymousUser()).count(), 0
        )

    def test_requester_has_no_visibility_at_all(self):
        self.assertEqual(get_change_queryset(self.requester).count(), 0)

    def test_technician_sees_only_assigned_changes(self):
        qs = get_change_queryset(self.technician)
        self.assertIn(self.change, qs)

        other_qs = get_change_queryset(self.other_technician)
        self.assertNotIn(self.change, other_qs)

    def test_technician_sees_own_unassigned_requested_change(self):
        """
        Without this, a Technician could raise a change and then be
        unable to see or submit it until someone else assigned an
        implementer — found and fixed while writing this test.
        """

        own_change = ChangeService.create_change(
            self.other_technician,
            title="Self-raised change",
            description="x",
            department=self.dept,
        )
        qs = get_change_queryset(self.other_technician)
        self.assertIn(own_change, qs)

    def test_managing_department_manager_sees_it(self):
        self.assertIn(self.change, get_change_queryset(self.manager))

    def test_unrelated_manager_does_not_see_it(self):
        self.assertNotIn(
            self.change, get_change_queryset(self.other_manager)
        )

    def test_administrator_sees_it(self):
        self.assertIn(self.change, get_change_queryset(self.admin))

    def test_requester_gets_403_on_list(self):
        self.client.login(
            username="vis_chg_requester", password="password123"
        )
        response = self.client.get(reverse("service_desk:change_list"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:change_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_unrelated_manager_gets_404_not_403_on_detail(self):
        self.client.login(
            username="vis_chg_other_manager", password="password123"
        )
        response = self.client.get(
            reverse("service_desk:change_detail", args=[self.change.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_other_technician_gets_404_not_403_on_detail(self):
        self.client.login(
            username="vis_chg_other_technician", password="password123"
        )
        response = self.client.get(
            reverse("service_desk:change_detail", args=[self.change.pk])
        )
        self.assertEqual(response.status_code, 404)


class ChangeWorkflowViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="IT")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_change", "add_change", "change_change")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_change", "add_change", "change_change")

        self.technician = User.objects.create_user(
            username="wfv_technician", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="wfv_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

    def test_full_lifecycle_through_real_views(self):
        self.client.login(username="wfv_technician", password="password123")

        create_response = self.client.post(
            reverse("service_desk:change_create"),
            {
                "title": "Patch firewall",
                "description": "Apply vendor security patch.",
                "change_type": "normal",
                "department": self.dept.pk,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        change = Change.objects.get(title="Patch firewall")

        submit_response = self.client.post(
            reverse("service_desk:change_submit", args=[change.pk])
        )
        self.assertEqual(submit_response.status_code, 302)

        self.client.logout()
        self.client.login(username="wfv_manager", password="password123")

        assess_response = self.client.post(
            reverse("service_desk:change_assess", args=[change.pk]),
            {"impact": "medium", "urgency": "medium"},
        )
        self.assertEqual(assess_response.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.risk_level, Change.RISK_MEDIUM)

        approve_response = self.client.post(
            reverse("service_desk:change_approve", args=[change.pk]),
            {"comment": "Looks safe."},
        )
        self.assertEqual(approve_response.status_code, 302)

        assign_response = self.client.post(
            reverse("service_desk:change_assign", args=[change.pk]),
            {"technician_id": self.technician.pk},
        )
        self.assertEqual(assign_response.status_code, 302)

        start = timezone.now() + timedelta(hours=1)
        end = start + timedelta(hours=2)
        schedule_response = self.client.post(
            reverse("service_desk:change_schedule", args=[change.pk]),
            {
                "scheduled_start": start.strftime("%Y-%m-%dT%H:%M"),
                "scheduled_end": end.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertEqual(schedule_response.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_SCHEDULED)

        self.client.logout()
        self.client.login(username="wfv_technician", password="password123")

        self.assertEqual(
            self.client.post(
                reverse("service_desk:change_implement", args=[change.pk])
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                reverse("service_desk:change_validate", args=[change.pk])
            ).status_code,
            302,
        )
        complete_response = self.client.post(
            reverse("service_desk:change_complete", args=[change.pk])
        )
        self.assertEqual(complete_response.status_code, 302)

        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_COMPLETED)

        self.assertTrue(
            change.history.filter(
                event_type=ChangeHistory.EVENT_COMPLETED
            ).exists()
        )

    def test_technician_cannot_approve_via_view(self):
        change = ChangeService.create_change(
            self.technician,
            title="Self change",
            description="x",
            department=self.dept,
        )
        ChangeService.submit_change(change, user=self.technician)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )

        self.client.login(username="wfv_technician", password="password123")
        response = self.client.post(
            reverse("service_desk:change_approve", args=[change.pk]),
            {"comment": "trying anyway"},
        )
        self.assertEqual(response.status_code, 302)

        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_ASSESSED)

    def test_submit_rejects_get(self):
        change = ChangeService.create_change(
            self.technician,
            title="GET check",
            description="x",
            department=self.dept,
        )
        self.client.login(username="wfv_technician", password="password123")
        response = self.client.get(
            reverse("service_desk:change_submit", args=[change.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_submit_requires_csrf_token(self):
        change = ChangeService.create_change(
            self.technician,
            title="CSRF check",
            description="x",
            department=self.dept,
        )
        client = Client(enforce_csrf_checks=True)
        client.login(username="wfv_technician", password="password123")
        response = client.post(
            reverse("service_desk:change_submit", args=[change.pk])
        )
        self.assertEqual(response.status_code, 403)
        change.refresh_from_db()
        self.assertEqual(change.status, Change.STATUS_DRAFT)

    def test_anonymous_create_redirects_to_login(self):
        response = self.client.post(
            reverse("service_desk:change_create"),
            {"title": "x", "description": "x"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
