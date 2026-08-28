"""
apps/service_desk/knowledge_views.py

Knowledge Management.

New flat view module rather than an addition to the existing
``views.py`` monolith — see ADR-011, Decision 2.

Every view resolves an article through
``get_knowledge_article_queryset`` — never ``KnowledgeArticle.
objects`` directly — so draft or restricted content can never leak
through a direct URL, matching the same discipline the selector
enforces for search.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms.knowledge_forms import KnowledgeArticleForm
from .models import KnowledgeArticle
from .security.mixins import (
    KnowledgeArticleChangePermissionMixin,
    KnowledgeArticleCreatePermissionMixin,
    KnowledgeArticleViewPermissionMixin,
)
from .security.policies import get_knowledge_article_queryset
from .selectors.knowledge_selector import KnowledgeSelector
from .services.knowledge_service import KnowledgeService

User = get_user_model()


class KnowledgeArticleListView(
    KnowledgeArticleViewPermissionMixin,
    ListView
):
    model = KnowledgeArticle
    template_name = "knowledge/list.html"
    context_object_name = "articles"
    paginate_by = 25
    permission_required = ("service_desk.view_knowledgearticle",)

    def get_queryset(self):
        queryset = KnowledgeSelector.with_related(
            get_knowledge_article_queryset(self.request.user)
        )

        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = KnowledgeSelector.search(queryset, search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = KnowledgeSelector.scoped_summary(
            get_knowledge_article_queryset(self.request.user)
        )
        context["search_query"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["status_choices"] = KnowledgeArticle.STATUS_CHOICES
        return context


class KnowledgeArticleCreateView(
    KnowledgeArticleCreatePermissionMixin,
    CreateView
):
    model = KnowledgeArticle
    form_class = KnowledgeArticleForm
    template_name = "knowledge/create.html"
    permission_required = ("service_desk.add_knowledgearticle",)
    success_url = reverse_lazy("service_desk:knowledge_list")

    def form_valid(self, form):
        try:
            self.object = KnowledgeService.create_article(
                self.request.user, **form.cleaned_data
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, f"Article '{self.object.title}' created.")
        return redirect("service_desk:knowledge_detail", pk=self.object.pk)


class KnowledgeArticleDetailView(
    KnowledgeArticleViewPermissionMixin,
    DetailView
):
    model = KnowledgeArticle
    template_name = "knowledge/detail.html"
    context_object_name = "article"
    permission_required = ("service_desk.view_knowledgearticle",)

    def get_queryset(self):
        return KnowledgeSelector.with_related(
            get_knowledge_article_queryset(self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history"] = self.object.history.select_related("performed_by")
        context["feedback_summary"] = KnowledgeSelector.feedback_summary(
            self.object
        )
        context["available_reviewers"] = User.objects.filter(
            groups__name__in=["Manager", "Administrator"],
            is_active=True,
        ).exclude(pk=self.object.author_id).distinct().order_by("username")
        context["next_statuses"] = KnowledgeService.STATUS_FLOW.get(
            self.object.status, []
        )

        my_feedback = None
        if self.request.user.is_authenticated:
            my_feedback = self.object.feedback_entries.filter(
                user=self.request.user
            ).first()
        context["my_feedback"] = my_feedback

        return context


class KnowledgeArticleUpdateView(
    KnowledgeArticleChangePermissionMixin,
    UpdateView
):
    model = KnowledgeArticle
    form_class = KnowledgeArticleForm
    template_name = "knowledge/update.html"
    context_object_name = "article"
    permission_required = ("service_desk.change_knowledgearticle",)

    def get_queryset(self):
        return get_knowledge_article_queryset(self.request.user)

    def form_valid(self, form):
        persisted = KnowledgeArticle.objects.get(pk=self.object.pk)

        try:
            self.object = KnowledgeService.update_article(
                persisted, user=self.request.user, **form.cleaned_data
            )
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "Article updated.")
        return redirect("service_desk:knowledge_detail", pk=self.object.pk)


class KnowledgeArticleSubmitView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        try:
            KnowledgeService.submit_for_review(article, user=request.user)
            messages.success(request, "Article submitted for review.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticleAssignReviewerView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        reviewer = get_object_or_404(
            User, pk=request.POST.get("reviewer_id"), is_active=True
        )
        try:
            KnowledgeService.assign_reviewer(article, reviewer, user=request.user)
            messages.success(
                request, f"Reviewer set to {reviewer.get_username()}."
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticleApproveView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        try:
            KnowledgeService.approve_article(
                article, request.user, comment=request.POST.get("comment", "")
            )
            messages.success(request, "Article approved.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticleSendBackView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        try:
            KnowledgeService.send_back(
                article, request.user, comment=request.POST.get("comment", "")
            )
            messages.success(request, "Article sent back for revision.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticlePublishView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        try:
            KnowledgeService.publish_article(article, user=request.user)
            messages.success(request, "Article published.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticleArchiveView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        try:
            KnowledgeService.archive_article(article, user=request.user)
            messages.success(request, "Article archived.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticleStartRevisionView(KnowledgeArticleChangePermissionMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        try:
            KnowledgeService.start_revision(article, user=request.user)
            messages.success(request, "Revision started.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("service_desk:knowledge_detail", pk=article.pk)


class KnowledgeArticleFeedbackView(KnowledgeArticleViewPermissionMixin, View):
    """
    Gated on view_knowledgearticle (every role that can read an
    article holds it, including Requester) rather than
    change_knowledgearticle — leaving feedback is a reader action,
    not an editorial one.
    """

    permission_required = ("service_desk.view_knowledgearticle",)

    def post(self, request, pk):
        article = get_object_or_404(
            get_knowledge_article_queryset(request.user), pk=pk
        )
        is_helpful = request.POST.get("is_helpful") == "true"

        try:
            KnowledgeService.submit_feedback(article, request.user, is_helpful)
            messages.success(request, "Thanks for the feedback.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("service_desk:knowledge_detail", pk=article.pk)
