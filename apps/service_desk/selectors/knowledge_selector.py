from django.db.models import Q, QuerySet

from apps.service_desk.models import KnowledgeArticle, KnowledgeFeedback


class KnowledgeSelector:
    """
    Read-only knowledge-article query layer.

    Every method here takes an already RBAC-scoped queryset (from
    ``security.policies.get_knowledge_article_queryset``) rather than
    a user — search never has its own, wider path to the table, which
    is exactly how draft/restricted content would leak.
    """

    @staticmethod
    def with_related(queryset: "QuerySet[KnowledgeArticle]") -> "QuerySet[KnowledgeArticle]":
        return queryset.select_related("category", "author", "reviewer")

    @classmethod
    def search(cls, queryset: "QuerySet[KnowledgeArticle]", query: str) -> "QuerySet[KnowledgeArticle]":
        return queryset.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(tags__icontains=query)
        )

    @classmethod
    def scoped_summary(cls, queryset: "QuerySet[KnowledgeArticle]") -> dict:
        return {
            "total": queryset.count(),
            "published": queryset.filter(
                status=KnowledgeArticle.STATUS_PUBLISHED
            ).count(),
            "in_review": queryset.filter(
                status=KnowledgeArticle.STATUS_IN_REVIEW
            ).count(),
        }

    @staticmethod
    def feedback_summary(article: KnowledgeArticle) -> dict:
        helpful = article.feedback_entries.filter(is_helpful=True).count()
        not_helpful = article.feedback_entries.filter(is_helpful=False).count()
        return {"helpful": helpful, "not_helpful": not_helpful}
