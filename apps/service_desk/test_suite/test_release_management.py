"""
Enterprise Completion Program — Phase 4: Release Management.

Covers: the "approved eligibility boundary" for linking changes
(a Change must have cleared CAB approval; a draft/submitted/assessed/
rejected change cannot be linked), separation of duties on approval,
schedule-conflict rejection, RBAC scoping (Requester excluded
entirely), cross-scope 404, anonymous redirect, POST-only/CSRF, and
the full lifecycle through real views.
"""

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.service_desk.models import Department, Release, ReleaseHistory
from apps.service_desk.security.policies import get_release_queryset
from apps.service_desk.services.change_service import ChangeService
from apps.service_desk.services.release_service import ReleaseService


def _grant(group, *codenames):
    group.permissions.add(
        *Permission.objects.filter(codename__in=codenames)
    )


class ReleaseServiceTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="IT")

        self.owner = User.objects.create_user(
            username="rel_owner", password="password123"
        )
        self.manager = User.objects.create_user(
            username="rel_manager", password="password123"
        )
        Group.objects.create(name="Manager")
        self.manager.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.manager)

        self.implementer = User.objects.create_user(
            username="rel_implementer", password="password123"
        )

    def _new_release(self, **overrides):
        data = {
            "name": "Q3 Platform Release",
            "version": "2026.09.1",
            "department": self.dept,
        }
        data.update(overrides)
        return ReleaseService.create_release(self.owner, **data)

    def _approved_change(self, title="Router upgrade"):
        change = ChangeService.create_change(
            self.owner, title=title, description="x", department=self.dept
        )
        ChangeService.submit_change(change, user=self.owner)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(change, self.manager)
        return change

    def test_unapproved_change_cannot_be_linked(self):
        release = self._new_release()
        draft_change = ChangeService.create_change(
            self.owner, title="Still draft", description="x", department=self.dept
        )

        with self.assertRaises(ValidationError):
            ReleaseService.link_change(release, draft_change)

        self.assertEqual(release.changes.count(), 0)

    def test_rejected_change_cannot_be_linked(self):
        release = self._new_release()
        change = ChangeService.create_change(
            self.owner, title="Bad idea", description="x", department=self.dept
        )
        ChangeService.submit_change(change, user=self.owner)
        ChangeService.reject_change(change, self.manager, "No.")

        with self.assertRaises(ValidationError):
            ReleaseService.link_change(release, change)

    def test_approved_change_can_be_linked_and_unlinked(self):
        release = self._new_release()
        change = self._approved_change()

        ReleaseService.link_change(release, change, user=self.owner)
        self.assertIn(change, release.changes.all())
        self.assertTrue(
            release.history.filter(
                event_type=ReleaseHistory.EVENT_CHANGE_LINKED
            ).exists()
        )

        ReleaseService.unlink_change(release, change, user=self.owner)
        self.assertNotIn(change, release.changes.all())

    def test_owner_cannot_approve_own_release(self):
        release = self._new_release()
        self.owner.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.owner)

        with self.assertRaises(ValidationError):
            ReleaseService.approve_release(release, self.owner)

    def test_technician_cannot_approve(self):
        release = self._new_release()
        with self.assertRaises(ValidationError):
            ReleaseService.approve_release(release, self.implementer)

    def test_manager_can_approve(self):
        release = self._new_release()
        ReleaseService.approve_release(release, self.manager, comment="ok")
        release.refresh_from_db()
        self.assertEqual(release.status, Release.STATUS_APPROVED)

    def test_illegal_transition_is_rejected(self):
        release = self._new_release()
        now = timezone.now()
        with self.assertRaises(ValidationError):
            ReleaseService.schedule_release(
                release, self.manager, now, now + timedelta(hours=1)
            )

    def test_conflicting_schedule_in_same_department_and_environment_rejected(self):
        existing = self._new_release(version="2026.09.1")
        ReleaseService.approve_release(existing, self.manager)

        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        ReleaseService.schedule_release(existing, self.manager, start, end)

        conflicting = self._new_release(version="2026.09.2")
        ReleaseService.approve_release(conflicting, self.manager)

        overlap_start = start + timedelta(minutes=30)
        overlap_end = overlap_start + timedelta(hours=1)

        with self.assertRaises(ValidationError):
            ReleaseService.schedule_release(
                conflicting, self.manager, overlap_start, overlap_end
            )

    def test_different_environment_does_not_conflict(self):
        existing = self._new_release(version="2026.09.1", environment=Release.ENVIRONMENT_STAGING)
        ReleaseService.approve_release(existing, self.manager)

        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        ReleaseService.schedule_release(existing, self.manager, start, end)

        other_env = self._new_release(
            version="2026.09.3", environment=Release.ENVIRONMENT_PRODUCTION
        )
        ReleaseService.approve_release(other_env, self.manager)

        ReleaseService.schedule_release(other_env, self.manager, start, end)
        other_env.refresh_from_db()
        self.assertEqual(other_env.status, Release.STATUS_SCHEDULED)

    def test_only_owner_manager_or_admin_may_advance_deployment(self):
        release = self._new_release()
        ReleaseService.approve_release(release, self.manager)
        ReleaseService.schedule_release(
            release,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )

        bystander = User.objects.create_user(
            username="rel_bystander", password="password123"
        )
        with self.assertRaises(ValidationError):
            ReleaseService.start_deployment(release, user=bystander)

        ReleaseService.start_deployment(release, user=self.owner)
        release.refresh_from_db()
        self.assertEqual(release.status, Release.STATUS_DEPLOYING)

    def test_fail_requires_a_reason(self):
        release = self._new_release()
        ReleaseService.approve_release(release, self.manager)
        ReleaseService.schedule_release(
            release,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )
        ReleaseService.start_deployment(release, user=self.owner)

        with self.assertRaises(ValidationError):
            ReleaseService.fail_release(release, self.owner, "")

    def test_full_success_and_failure_paths(self):
        success = self._new_release(version="2026.09.10")
        ReleaseService.approve_release(success, self.manager)
        ReleaseService.schedule_release(
            success,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )
        ReleaseService.start_deployment(success, user=self.owner)
        ReleaseService.request_validation(success, user=self.owner)
        ReleaseService.complete_release(success, user=self.owner, outcome="Shipped cleanly.")
        success.refresh_from_db()
        self.assertEqual(success.status, Release.STATUS_COMPLETED)
        self.assertFalse(success.is_open)
        self.assertEqual(success.outcome, "Shipped cleanly.")

        failing = self._new_release(version="2026.09.11")
        ReleaseService.approve_release(failing, self.manager)
        ReleaseService.schedule_release(
            failing,
            self.manager,
            timezone.now() + timedelta(hours=1),
            timezone.now() + timedelta(hours=2),
        )
        ReleaseService.start_deployment(failing, user=self.owner)
        ReleaseService.fail_release(failing, self.owner, "Smoke test failed.")
        ReleaseService.rollback_release(failing, self.owner, "Reverted deployment.")
        failing.refresh_from_db()
        self.assertEqual(failing.status, Release.STATUS_ROLLED_BACK)


class ReleaseVisibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="IT")
        self.other_dept = Department.objects.create(name="Finance")

        requester_group = Group.objects.create(name="Requester")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_release", "change_release")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_release", "add_release", "change_release")

        self.requester = User.objects.create_user(
            username="vis_rel_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.owner = User.objects.create_user(
            username="vis_rel_owner", password="password123"
        )
        self.owner.groups.add(technician_group)

        self.other_technician = User.objects.create_user(
            username="vis_rel_other_tech", password="password123"
        )
        self.other_technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="vis_rel_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.other_manager = User.objects.create_user(
            username="vis_rel_other_manager", password="password123"
        )
        self.other_manager.groups.add(manager_group)
        self.other_dept.managers.add(self.other_manager)

        self.admin = User.objects.create_superuser(
            username="vis_rel_admin", password="password123", email="a@test.com"
        )

        self.release = ReleaseService.create_release(
            self.owner,
            name="Release",
            version="1.0.0",
            department=self.dept,
        )

    def test_anonymous_sees_nothing(self):
        self.assertEqual(get_release_queryset(AnonymousUser()).count(), 0)

    def test_requester_has_no_visibility(self):
        self.assertEqual(get_release_queryset(self.requester).count(), 0)

    def test_owner_sees_it(self):
        self.assertIn(self.release, get_release_queryset(self.owner))

    def test_other_technician_does_not_see_it(self):
        self.assertNotIn(
            self.release, get_release_queryset(self.other_technician)
        )

    def test_managing_department_manager_sees_it(self):
        self.assertIn(self.release, get_release_queryset(self.manager))

    def test_unrelated_manager_does_not_see_it(self):
        self.assertNotIn(
            self.release, get_release_queryset(self.other_manager)
        )

    def test_administrator_sees_it(self):
        self.assertIn(self.release, get_release_queryset(self.admin))

    def test_requester_gets_403_on_list(self):
        self.client.login(
            username="vis_rel_requester", password="password123"
        )
        response = self.client.get(reverse("service_desk:release_list"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:release_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_unrelated_manager_gets_404_not_403_on_detail(self):
        self.client.login(
            username="vis_rel_other_manager", password="password123"
        )
        response = self.client.get(
            reverse("service_desk:release_detail", args=[self.release.pk])
        )
        self.assertEqual(response.status_code, 404)


class ReleaseWorkflowViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="IT")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_release", "change_release", "view_change", "add_change", "change_change")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_release", "add_release", "change_release", "view_change", "add_change", "change_change")

        self.technician = User.objects.create_user(
            username="wfv_rel_tech", password="password123"
        )
        self.technician.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="wfv_rel_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

    def test_full_lifecycle_through_real_views(self):
        change = ChangeService.create_change(
            self.technician,
            title="Router firmware",
            description="x",
            department=self.dept,
        )
        ChangeService.submit_change(change, user=self.technician)
        ChangeService.assess_change(
            change, self.manager, impact="low", urgency="low"
        )
        ChangeService.approve_change(change, self.manager)

        self.client.login(username="wfv_rel_manager", password="password123")

        create_response = self.client.post(
            reverse("service_desk:release_create"),
            {
                "name": "Q3 Release",
                "version": "2026.09.1",
                "environment": "staging",
                "department": self.dept.pk,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        release = Release.objects.get(version="2026.09.1")

        # manager cannot approve own release
        approve_own_response = self.client.post(
            reverse("service_desk:release_approve", args=[release.pk]),
            {"comment": "self approve"},
        )
        self.assertEqual(approve_own_response.status_code, 302)
        release.refresh_from_db()
        self.assertEqual(release.status, Release.STATUS_DRAFT)

        link_response = self.client.post(
            reverse("service_desk:release_link_change", args=[release.pk]),
            {"change_id": change.pk},
        )
        self.assertEqual(link_response.status_code, 302)
        self.assertIn(change, release.changes.all())

        self.client.logout()
        self.client.login(username="wfv_rel_tech", password="password123")

        # The technician is not this release's owner, so
        # get_release_queryset (owner-scoped for Technicians) doesn't
        # even resolve the object yet — 404, not 403: existence must
        # not be disclosed across scope. Ownership is assigned below.
        approve_response = self.client.post(
            reverse("service_desk:release_approve", args=[release.pk]),
            {"comment": "trying"},
        )
        self.assertEqual(approve_response.status_code, 404)
        release.refresh_from_db()
        self.assertEqual(release.status, Release.STATUS_DRAFT)

        self.client.logout()
        self.client.login(username="wfv_rel_manager", password="password123")

        assign_response = self.client.post(
            reverse("service_desk:release_assign_owner", args=[release.pk]),
            {"owner_id": self.technician.pk},
        )
        self.assertEqual(assign_response.status_code, 302)

        approve_response = self.client.post(
            reverse("service_desk:release_approve", args=[release.pk]),
            {"comment": "ok"},
        )
        self.assertEqual(approve_response.status_code, 302)
        release.refresh_from_db()
        self.assertEqual(release.status, Release.STATUS_APPROVED)

        start = timezone.now() + timedelta(hours=1)
        end = start + timedelta(hours=2)
        schedule_response = self.client.post(
            reverse("service_desk:release_schedule", args=[release.pk]),
            {
                "scheduled_start": start.strftime("%Y-%m-%dT%H:%M"),
                "scheduled_end": end.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertEqual(schedule_response.status_code, 302)

        self.client.logout()
        self.client.login(username="wfv_rel_tech", password="password123")

        self.assertEqual(
            self.client.post(
                reverse("service_desk:release_deploy", args=[release.pk])
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                reverse("service_desk:release_validate", args=[release.pk])
            ).status_code,
            302,
        )
        complete_response = self.client.post(
            reverse("service_desk:release_complete", args=[release.pk]),
            {"outcome": "All good."},
        )
        self.assertEqual(complete_response.status_code, 302)

        release.refresh_from_db()
        self.assertEqual(release.status, Release.STATUS_COMPLETED)
        self.assertTrue(
            release.history.filter(
                event_type=ReleaseHistory.EVENT_COMPLETED
            ).exists()
        )

    def test_approve_rejects_get(self):
        release = ReleaseService.create_release(
            self.manager, name="X", version="1.0", department=self.dept
        )
        self.client.login(username="wfv_rel_manager", password="password123")
        response = self.client.get(
            reverse("service_desk:release_approve", args=[release.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_approve_requires_csrf_token(self):
        release = ReleaseService.create_release(
            self.manager, name="Y", version="1.0", department=self.dept
        )
        client = Client(enforce_csrf_checks=True)
        client.login(username="wfv_rel_tech", password="password123")
        response = client.post(
            reverse("service_desk:release_approve", args=[release.pk]),
            {"comment": "x"},
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_create_redirects_to_login(self):
        response = self.client.post(
            reverse("service_desk:release_create"),
            {"name": "x", "version": "1.0"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
