from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.release_management.models import Release
from apps.release_management.services import ReleaseService
from apps.service_desk.models import Company

User = get_user_model()


class ReleaseServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="RelCo", slug="rel-co")
        self.user = User.objects.create_user(
            username="relmgr", password="pass12345", is_staff=True
        )

    def test_create_and_deploy(self):
        release = ReleaseService.create_release(
            self.company,
            name="Spring release",
            version="2026.7.1",
            manager=self.user,
            actor=self.user,
        )
        self.assertEqual(release.tasks.count(), 5)
        ReleaseService.transition(release, Release.State.DEPLOYING, actor=self.user)
        release.refresh_from_db()
        self.assertIsNotNone(release.actual_start)
        ReleaseService.transition(release, Release.State.DEPLOYED, actor=self.user)
        release.refresh_from_db()
        self.assertEqual(release.state, Release.State.DEPLOYED)


class ReleaseUITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="RelUI", slug="rel-ui")
        self.user = User.objects.create_user(
            username="relui", password="pass12345", is_staff=True
        )
        self.client = Client()
        self.client.login(username="relui", password="pass12345")
        s = self.client.session
        s["company_id"] = self.company.pk
        s.save()
        ReleaseService.create_release(
            self.company, name="UI Rel", version="1.0.0", actor=self.user
        )

    def test_list(self):
        res = self.client.get(reverse("releases:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "1.0.0")
