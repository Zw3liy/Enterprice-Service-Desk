"""Knowledge base application service."""

from __future__ import annotations

from django.db.models import F, Q, QuerySet
from django.utils import timezone
from django.utils.text import slugify

from apps.service_desk.models import KnowledgeArticle


class KnowledgeService:
    @staticmethod
    def published(company=None) -> QuerySet[KnowledgeArticle]:
        qs = KnowledgeArticle.objects.filter(is_published=True).select_related(
            "category", "company", "author"
        )
        if company is not None:
            qs = qs.filter(company=company)
        return qs

    @classmethod
    def search(cls, query: str, *, company=None, include_internal: bool = False):
        qs = KnowledgeArticle.objects.all().select_related("category", "author")
        if company is not None:
            qs = qs.filter(company=company)
        if not include_internal:
            qs = qs.filter(is_published=True, is_internal=False)
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(summary__icontains=query)
                | Q(body__icontains=query)
                | Q(tags__icontains=query)
            )
        return qs.order_by("-published_at", "-view_count")

    @classmethod
    def create_article(
        cls,
        *,
        company,
        title: str,
        body: str,
        summary: str = "",
        category=None,
        author=None,
        is_published: bool = False,
        is_internal: bool = False,
        tags: list | None = None,
    ) -> KnowledgeArticle:
        article = KnowledgeArticle(
            company=company,
            title=title.strip(),
            slug=slugify(title)[:260],
            body=body,
            summary=summary,
            category=category,
            author=author,
            is_published=is_published,
            is_internal=is_internal,
            tags=tags or [],
        )
        if is_published:
            article.published_at = timezone.now()
        article.save()
        return article

    @staticmethod
    def record_view(article: KnowledgeArticle) -> None:
        KnowledgeArticle.objects.filter(pk=article.pk).update(view_count=F("view_count") + 1)

    @staticmethod
    def feedback(article: KnowledgeArticle, helpful: bool) -> None:
        if helpful:
            KnowledgeArticle.objects.filter(pk=article.pk).update(
                helpful_yes=F("helpful_yes") + 1
            )
        else:
            KnowledgeArticle.objects.filter(pk=article.pk).update(
                helpful_no=F("helpful_no") + 1
            )
