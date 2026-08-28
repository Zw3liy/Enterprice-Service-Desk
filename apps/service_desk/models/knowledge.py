from django.conf import settings
from django.db import models
from django.utils import timezone


class KnowledgeCategory(models.Model):
    """
    Top-level grouping for knowledge articles.

    Administered like ``ServiceCategory``/``ConfigurationItemType`` —
    reference data with no dedicated app views.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Knowledge Category"
        verbose_name_plural = "Knowledge Categories"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class KnowledgeArticle(models.Model):
    """
    A knowledge-base article with a draft -> review -> approval ->
    publication -> archival lifecycle, plus a revision cycle that can
    restart from ``published`` or ``archived``.

    ``visibility`` and ``status`` together gate who may ever see an
    article — see ``security.policies.get_knowledge_article_queryset``
    for the exact rule. Draft/restricted content must never leak
    through search or a direct URL: every view resolves articles
    through that one function, never a raw queryset.
    """

    STATUS_DRAFT = "draft"
    STATUS_IN_REVIEW = "in_review"
    STATUS_APPROVED = "approved"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_IN_REVIEW, "In Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    VISIBILITY_PUBLIC = "public"
    VISIBILITY_INTERNAL = "internal"
    VISIBILITY_RESTRICTED = "restricted"

    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public (all users)"),
        (VISIBILITY_INTERNAL, "Internal (staff only)"),
        (VISIBILITY_RESTRICTED, "Restricted (managers and administrators)"),
    ]

    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.PROTECT,
        related_name="articles",
    )

    title = models.CharField(
        max_length=200,
    )

    content = models.TextField()

    tags = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_knowledge_articles",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_articles_to_review",
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_INTERNAL,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Knowledge Article"
        verbose_name_plural = "Knowledge Articles"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["visibility"]),
            models.Index(fields=["category"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]


class KnowledgeArticleHistory(models.Model):
    """
    Immutable audit trail for article lifecycle events.
    """

    EVENT_CREATED = "created"
    EVENT_SUBMITTED = "submitted_for_review"
    EVENT_REVIEWER_ASSIGNED = "reviewer_assigned"
    EVENT_APPROVED = "approved"
    EVENT_SENT_BACK = "sent_back"
    EVENT_PUBLISHED = "published"
    EVENT_ARCHIVED = "archived"
    EVENT_REVISION_STARTED = "revision_started"

    EVENT_CHOICES = [
        (EVENT_CREATED, "Created"),
        (EVENT_SUBMITTED, "Submitted For Review"),
        (EVENT_REVIEWER_ASSIGNED, "Reviewer Assigned"),
        (EVENT_APPROVED, "Approved"),
        (EVENT_SENT_BACK, "Sent Back"),
        (EVENT_PUBLISHED, "Published"),
        (EVENT_ARCHIVED, "Archived"),
        (EVENT_REVISION_STARTED, "Revision Started"),
    ]

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_article_history",
    )

    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    comment = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Knowledge Article History"
        verbose_name_plural = "Knowledge Article History"
        indexes = [
            models.Index(fields=["article", "created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.article} - {self.get_event_type_display()}"

    @classmethod
    def record(
        cls,
        *,
        article,
        event_type,
        user=None,
        comment="",
        old_value="",
        new_value="",
    ):
        return cls.objects.create(
            article=article,
            event_type=event_type,
            performed_by=user,
            comment=comment,
            old_value=old_value,
            new_value=new_value,
        )


class KnowledgeFeedback(models.Model):
    """
    One user's helpful/not-helpful vote on a published article.

    Duplicate protection: a ``UniqueConstraint`` on (article, user)
    means a second vote updates the first rather than creating a new
    row — enforced in ``KnowledgeService.submit_feedback`` via
    ``update_or_create``, backed by this constraint so a race
    condition can't slip a duplicate past the service layer either.
    """

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name="feedback_entries",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_feedback",
    )

    is_helpful = models.BooleanField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Knowledge Feedback"
        verbose_name_plural = "Knowledge Feedback"
        constraints = [
            models.UniqueConstraint(
                fields=["article", "user"],
                name="unique_knowledge_feedback_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["article", "is_helpful"]),
        ]

    def __str__(self):
        return f"{self.user} - {'helpful' if self.is_helpful else 'not helpful'} - {self.article}"
