"""
Enterprise Completion Program — Phase 6: Knowledge Management.

Covers: the exact visibility matrix that stops draft/restricted
content leaking through search or a direct URL (mission requirement,
verified for every role including anonymous), self-review
prevention, duplicate-feedback protection, POST-only/CSRF, cross-
scope 404, anonymous redirect, and the full lifecycle through real
views (draft -> review -> approval -> publication -> archival ->
revision).
"""

from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.service_desk.models import (
    Department,
    KnowledgeArticle,
    KnowledgeArticleHistory,
    KnowledgeCategory,
    KnowledgeFeedback,
)
from apps.service_desk.security.policies import get_knowledge_article_queryset
from apps.service_desk.services.knowledge_service import KnowledgeService


def _grant(group, *codenames):
    group.permissions.add(
        *Permission.objects.filter(codename__in=codenames)
    )


class KnowledgeServiceTests(TestCase):
    def setUp(self):
        self.category = KnowledgeCategory.objects.create(name="How-To")

        self.dept = Department.objects.create(name="IT")

        self.author = User.objects.create_user(
            username="kb_author", password="password123"
        )
        self.manager = User.objects.create_user(
            username="kb_manager", password="password123"
        )
        Group.objects.create(name="Manager")
        self.manager.groups.add(Group.objects.get(name="Manager"))
        self.dept.managers.add(self.manager)

        self.other_technician = User.objects.create_user(
            username="kb_other_tech", password="password123"
        )

    def _draft(self):
        return KnowledgeService.create_article(
            self.author,
            category=self.category,
            title="How to reset a password",
            content="Steps...",
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )

    def test_author_cannot_review_own_article(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)

        self.author.groups.add(Group.objects.get(name="Manager"))

        with self.assertRaises(ValidationError):
            KnowledgeService.approve_article(article, self.author)

    def test_author_cannot_be_assigned_as_reviewer(self):
        article = self._draft()
        with self.assertRaises(ValidationError):
            KnowledgeService.assign_reviewer(article, self.author, user=self.manager)

    def test_only_assigned_reviewer_or_manager_may_approve(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)

        with self.assertRaises(ValidationError):
            KnowledgeService.approve_article(article, self.other_technician)

        KnowledgeService.approve_article(article, self.manager)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_APPROVED)

    def test_send_back_requires_a_comment(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)

        with self.assertRaises(ValidationError):
            KnowledgeService.send_back(article, self.manager, "")

    def test_send_back_returns_to_draft_and_records_history(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)
        KnowledgeService.send_back(article, self.manager, "Needs more detail.")

        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_DRAFT)
        self.assertTrue(
            article.history.filter(
                event_type=KnowledgeArticleHistory.EVENT_SENT_BACK
            ).exists()
        )

    def test_illegal_transition_is_rejected(self):
        article = self._draft()
        with self.assertRaises(ValidationError):
            KnowledgeService.publish_article(article, user=self.manager)

    def test_only_manager_or_administrator_can_publish(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)
        KnowledgeService.approve_article(article, self.manager)

        with self.assertRaises(ValidationError):
            KnowledgeService.publish_article(article, user=self.other_technician)

        KnowledgeService.publish_article(article, user=self.manager)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_PUBLISHED)
        self.assertEqual(article.version, 2)
        self.assertIsNotNone(article.published_at)

    def test_start_revision_from_published_and_archived(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)
        KnowledgeService.approve_article(article, self.manager)
        KnowledgeService.publish_article(article, user=self.manager)

        KnowledgeService.start_revision(article, user=self.author)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_DRAFT)

        # publish again, then archive, then revise from archived
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)
        KnowledgeService.approve_article(article, self.manager)
        KnowledgeService.publish_article(article, user=self.manager)
        KnowledgeService.archive_article(article, user=self.author)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_ARCHIVED)

        KnowledgeService.start_revision(article, user=self.author)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_DRAFT)
        self.assertEqual(article.version, 3)

    def test_feedback_requires_published_status(self):
        article = self._draft()
        with self.assertRaises(ValidationError):
            KnowledgeService.submit_feedback(article, self.other_technician, True)

    def test_duplicate_feedback_updates_instead_of_duplicating(self):
        article = self._draft()
        KnowledgeService.submit_for_review(article, user=self.author)
        KnowledgeService.assign_reviewer(article, self.manager, user=self.manager)
        KnowledgeService.approve_article(article, self.manager)
        KnowledgeService.publish_article(article, user=self.manager)

        KnowledgeService.submit_feedback(article, self.other_technician, True)
        KnowledgeService.submit_feedback(article, self.other_technician, False)

        self.assertEqual(
            KnowledgeFeedback.objects.filter(
                article=article, user=self.other_technician
            ).count(),
            1,
        )
        feedback = KnowledgeFeedback.objects.get(
            article=article, user=self.other_technician
        )
        self.assertFalse(feedback.is_helpful)


class KnowledgeVisibilityTests(TestCase):
    """
    The mission's core requirement: "Draft or restricted content must
    not leak through search or direct URLs." Verified for every role
    including anonymous.
    """

    def setUp(self):
        self.client = Client()
        self.category = KnowledgeCategory.objects.create(name="How-To")
        self.dept = Department.objects.create(name="IT")

        self.author = User.objects.create_user(
            username="vis_kb_author", password="password123"
        )

        requester_group = Group.objects.create(name="Requester")
        _grant(requester_group, "view_knowledgearticle")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_knowledgearticle", "add_knowledgearticle")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_knowledgearticle", "change_knowledgearticle")

        self.requester = User.objects.create_user(
            username="vis_kb_requester", password="password123"
        )
        self.requester.groups.add(requester_group)

        self.technician = User.objects.create_user(
            username="vis_kb_technician", password="password123"
        )
        self.technician.groups.add(technician_group)
        self.author.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="vis_kb_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.admin = User.objects.create_superuser(
            username="vis_kb_admin", password="password123", email="a@test.com"
        )

        self.draft = KnowledgeArticle.objects.create(
            category=self.category, title="Draft article", content="secret draft",
            author=self.author, status=KnowledgeArticle.STATUS_DRAFT,
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )
        self.published_public = KnowledgeArticle.objects.create(
            category=self.category, title="Published public", content="public content",
            author=self.author, status=KnowledgeArticle.STATUS_PUBLISHED,
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )
        self.published_internal = KnowledgeArticle.objects.create(
            category=self.category, title="Published internal", content="staff content",
            author=self.author, status=KnowledgeArticle.STATUS_PUBLISHED,
            visibility=KnowledgeArticle.VISIBILITY_INTERNAL,
        )
        self.published_restricted = KnowledgeArticle.objects.create(
            category=self.category, title="Published restricted", content="mgmt content",
            author=self.author, status=KnowledgeArticle.STATUS_PUBLISHED,
            visibility=KnowledgeArticle.VISIBILITY_RESTRICTED,
        )

    def test_anonymous_sees_nothing(self):
        self.assertEqual(
            get_knowledge_article_queryset(AnonymousUser()).count(), 0
        )

    def test_requester_sees_only_published_public(self):
        qs = get_knowledge_article_queryset(self.requester)
        self.assertIn(self.published_public, qs)
        self.assertNotIn(self.published_internal, qs)
        self.assertNotIn(self.published_restricted, qs)
        self.assertNotIn(self.draft, qs)

    def test_technician_sees_published_public_and_internal_not_restricted(self):
        qs = get_knowledge_article_queryset(self.technician)
        self.assertIn(self.published_public, qs)
        self.assertIn(self.published_internal, qs)
        self.assertNotIn(self.published_restricted, qs)
        self.assertNotIn(self.draft, qs)

    def test_author_sees_their_own_draft(self):
        qs = get_knowledge_article_queryset(self.author)
        self.assertIn(self.draft, qs)

    def test_manager_sees_all_published_regardless_of_visibility(self):
        qs = get_knowledge_article_queryset(self.manager)
        self.assertIn(self.published_public, qs)
        self.assertIn(self.published_internal, qs)
        self.assertIn(self.published_restricted, qs)
        self.assertNotIn(self.draft, qs)

    def test_manager_sees_others_in_review_articles(self):
        """
        Regression for a real gap found while testing: a Manager
        scoped to "published, or their own" could never see another
        author's in-review submission — making reviewer assignment
        impossible. Managers must see everything past draft.
        """

        in_review = KnowledgeArticle.objects.create(
            category=self.category, title="Pending review", content="x",
            author=self.author, status=KnowledgeArticle.STATUS_IN_REVIEW,
            visibility=KnowledgeArticle.VISIBILITY_INTERNAL,
        )
        self.assertIn(in_review, get_knowledge_article_queryset(self.manager))

    def test_manager_does_not_see_others_drafts(self):
        self.assertNotIn(self.draft, get_knowledge_article_queryset(self.manager))

    def test_administrator_sees_everything_including_drafts(self):
        qs = get_knowledge_article_queryset(self.admin)
        self.assertIn(self.draft, qs)
        self.assertIn(self.published_restricted, qs)

    def test_requester_direct_url_to_draft_is_404(self):
        self.client.login(username="vis_kb_requester", password="password123")
        response = self.client.get(
            reverse("service_desk:knowledge_detail", args=[self.draft.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_requester_direct_url_to_restricted_published_is_404(self):
        self.client.login(username="vis_kb_requester", password="password123")
        response = self.client.get(
            reverse(
                "service_desk:knowledge_detail",
                args=[self.published_restricted.pk],
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_requester_search_does_not_surface_draft(self):
        self.client.login(username="vis_kb_requester", password="password123")
        response = self.client.get(
            reverse("service_desk:knowledge_list"), {"q": "secret"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Draft article")

    def test_requester_search_does_not_surface_restricted(self):
        self.client.login(username="vis_kb_requester", password="password123")
        response = self.client.get(
            reverse("service_desk:knowledge_list"), {"q": "mgmt"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Published restricted")

    def test_requester_search_finds_public_published(self):
        self.client.login(username="vis_kb_requester", password="password123")
        response = self.client.get(
            reverse("service_desk:knowledge_list"), {"q": "public content"}
        )
        self.assertContains(response, "Published public")

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("service_desk:knowledge_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)


class KnowledgeWorkflowViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = KnowledgeCategory.objects.create(name="How-To")
        self.dept = Department.objects.create(name="IT")

        technician_group = Group.objects.create(name="Technician")
        _grant(technician_group, "view_knowledgearticle", "add_knowledgearticle", "change_knowledgearticle")

        manager_group = Group.objects.create(name="Manager")
        _grant(manager_group, "view_knowledgearticle", "add_knowledgearticle", "change_knowledgearticle")

        self.author = User.objects.create_user(
            username="wf_kb_author", password="password123"
        )
        self.author.groups.add(technician_group)

        self.manager = User.objects.create_user(
            username="wf_kb_manager", password="password123"
        )
        self.manager.groups.add(manager_group)
        self.dept.managers.add(self.manager)

        self.requester_group = Group.objects.create(name="Requester")
        _grant(self.requester_group, "view_knowledgearticle")
        self.requester = User.objects.create_user(
            username="wf_kb_requester", password="password123"
        )
        self.requester.groups.add(self.requester_group)

    def test_full_lifecycle_through_real_views(self):
        self.client.login(username="wf_kb_author", password="password123")

        create_response = self.client.post(
            reverse("service_desk:knowledge_create"),
            {
                "category": self.category.pk,
                "title": "VPN setup guide",
                "content": "Step 1...",
                "visibility": "public",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        article = KnowledgeArticle.objects.get(title="VPN setup guide")

        submit_response = self.client.post(
            reverse("service_desk:knowledge_submit", args=[article.pk])
        )
        self.assertEqual(submit_response.status_code, 302)

        self.client.logout()
        self.client.login(username="wf_kb_manager", password="password123")

        assign_response = self.client.post(
            reverse("service_desk:knowledge_assign_reviewer", args=[article.pk]),
            {"reviewer_id": self.manager.pk},
        )
        self.assertEqual(assign_response.status_code, 302)

        approve_response = self.client.post(
            reverse("service_desk:knowledge_approve", args=[article.pk]),
            {"comment": "Looks good."},
        )
        self.assertEqual(approve_response.status_code, 302)

        publish_response = self.client.post(
            reverse("service_desk:knowledge_publish", args=[article.pk])
        )
        self.assertEqual(publish_response.status_code, 302)

        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_PUBLISHED)

        # Requester can now read it and leave feedback.
        self.client.logout()
        self.client.login(username="wf_kb_requester", password="password123")

        detail_response = self.client.get(
            reverse("service_desk:knowledge_detail", args=[article.pk])
        )
        self.assertEqual(detail_response.status_code, 200)

        feedback_response = self.client.post(
            reverse("service_desk:knowledge_feedback", args=[article.pk]),
            {"is_helpful": "true"},
        )
        self.assertEqual(feedback_response.status_code, 302)
        self.assertTrue(
            KnowledgeFeedback.objects.filter(
                article=article, user=self.requester, is_helpful=True
            ).exists()
        )

        self.client.logout()
        self.client.login(username="wf_kb_manager", password="password123")

        archive_response = self.client.post(
            reverse("service_desk:knowledge_archive", args=[article.pk])
        )
        self.assertEqual(archive_response.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_ARCHIVED)

        self.assertTrue(
            article.history.filter(
                event_type=KnowledgeArticleHistory.EVENT_PUBLISHED
            ).exists()
        )

    def test_author_cannot_approve_own_article_via_view(self):
        article = KnowledgeService.create_article(
            self.author,
            category=self.category,
            title="Self review test",
            content="x",
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )
        KnowledgeService.submit_for_review(article, user=self.author)
        self.author.groups.add(Group.objects.get(name="Manager"))

        self.client.login(username="wf_kb_author", password="password123")
        response = self.client.post(
            reverse("service_desk:knowledge_approve", args=[article.pk]),
            {"comment": "self approve"},
        )
        self.assertEqual(response.status_code, 302)

        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_IN_REVIEW)

    def test_submit_rejects_get(self):
        article = KnowledgeService.create_article(
            self.author, category=self.category, title="X", content="x",
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )
        self.client.login(username="wf_kb_author", password="password123")
        response = self.client.get(
            reverse("service_desk:knowledge_submit", args=[article.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_submit_requires_csrf_token(self):
        article = KnowledgeService.create_article(
            self.author, category=self.category, title="Y", content="x",
            visibility=KnowledgeArticle.VISIBILITY_PUBLIC,
        )
        client = Client(enforce_csrf_checks=True)
        client.login(username="wf_kb_author", password="password123")
        response = client.post(
            reverse("service_desk:knowledge_submit", args=[article.pk])
        )
        self.assertEqual(response.status_code, 403)
        article.refresh_from_db()
        self.assertEqual(article.status, KnowledgeArticle.STATUS_DRAFT)

    def test_anonymous_create_redirects_to_login(self):
        response = self.client.post(
            reverse("service_desk:knowledge_create"),
            {"title": "x"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
