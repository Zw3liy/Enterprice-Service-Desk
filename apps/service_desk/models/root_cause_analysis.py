from django.conf import settings
from django.db import models

from .problem import Problem


class RootCauseAnalysis(models.Model):
    """
    Structured root cause investigation for a Problem.

    One Problem has exactly one Root Cause Analysis
    (see ADR-009).
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    METHOD_CHOICES = [
        ("five_whys", "Five Whys"),
        ("fishbone", "Fishbone (Ishikawa)"),
        ("fault_tree", "Fault Tree Analysis"),
        ("other", "Other"),
    ]

    problem = models.OneToOneField(
        Problem,
        on_delete=models.CASCADE,
        related_name="rca",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default="five_whys",
        db_index=True,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_rca_entries",
    )

    problem_statement = models.TextField()

    trigger_event = models.TextField(
        blank=True,
        default="",
    )

    contributing_factors = models.TextField(
        blank=True,
        default="",
    )

    mitigation_steps = models.TextField(
        blank=True,
        default="",
    )

    preventative_measures = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Root Cause Analysis"
        verbose_name_plural = "Root Cause Analyses"
        indexes = [
            models.Index(fields=["problem"]),
            models.Index(fields=["status"]),
            models.Index(fields=["method"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"RCA[{self.pk}] for {self.problem}"


class FiveWhys(models.Model):
    """
    Single "why" step in a Five Whys investigation.
    """

    rca = models.ForeignKey(
        RootCauseAnalysis,
        on_delete=models.CASCADE,
        related_name="five_whys",
    )

    step_number = models.PositiveSmallIntegerField()

    question = models.TextField()

    answer = models.TextField()

    class Meta:
        ordering = ["step_number"]
        verbose_name = "Five Whys Step"
        verbose_name_plural = "Five Whys Steps"
        constraints = [
            models.UniqueConstraint(
                fields=["rca", "step_number"],
                name="unique_five_whys_step_per_rca",
            ),
        ]
        indexes = [
            models.Index(fields=["rca", "step_number"]),
        ]

    def __str__(self):
        return f"{self.rca} - Why #{self.step_number}"


class FishboneFactor(models.Model):
    """
    Single contributing factor in a Fishbone (Ishikawa) analysis.
    """

    CATEGORY_PEOPLE = "people"
    CATEGORY_PROCESS = "process"
    CATEGORY_EQUIPMENT = "equipment"
    CATEGORY_MATERIAL = "material"
    CATEGORY_ENVIRONMENT = "environment"
    CATEGORY_MANAGEMENT = "management"

    CATEGORY_CHOICES = [
        (CATEGORY_PEOPLE, "People"),
        (CATEGORY_PROCESS, "Process"),
        (CATEGORY_EQUIPMENT, "Equipment"),
        (CATEGORY_MATERIAL, "Material"),
        (CATEGORY_ENVIRONMENT, "Environment"),
        (CATEGORY_MANAGEMENT, "Management"),
    ]

    rca = models.ForeignKey(
        RootCauseAnalysis,
        on_delete=models.CASCADE,
        related_name="fishbone_factors",
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
    )

    factor_description = models.TextField()

    is_root_cause = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["category"]
        verbose_name = "Fishbone Factor"
        verbose_name_plural = "Fishbone Factors"
        indexes = [
            models.Index(fields=["rca", "category"]),
            models.Index(fields=["is_root_cause"]),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.factor_description[:50]}"


class Evidence(models.Model):
    """
    Supporting evidence attached to a root cause investigation.
    """

    rca = models.ForeignKey(
        RootCauseAnalysis,
        on_delete=models.CASCADE,
        related_name="evidence",
    )

    title = models.CharField(
        max_length=200,
    )

    file_or_link = models.CharField(
        max_length=500,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Evidence"
        verbose_name_plural = "Evidence"
        indexes = [
            models.Index(fields=["rca"]),
            models.Index(fields=["uploaded_at"]),
        ]

    def __str__(self):
        return self.title


class Action(models.Model):
    """
    Corrective or Preventive Action (CAPA) raised from an RCA.
    """

    ACTION_TYPE_CORRECTIVE = "corrective"
    ACTION_TYPE_PREVENTIVE = "preventive"

    ACTION_TYPE_CHOICES = [
        (ACTION_TYPE_CORRECTIVE, "Corrective"),
        (ACTION_TYPE_PREVENTIVE, "Preventive"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    rca = models.ForeignKey(
        RootCauseAnalysis,
        on_delete=models.CASCADE,
        related_name="actions",
    )

    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPE_CHOICES,
    )

    description = models.TextField()

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_problem_actions",
    )

    due_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True,
    )

    class Meta:
        ordering = ["due_date"]
        verbose_name = "Action"
        verbose_name_plural = "Actions"
        indexes = [
            models.Index(fields=["rca"]),
            models.Index(fields=["status"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"{self.get_action_type_display()} action: {self.description[:50]}"


class Approval(models.Model):
    """
    Sign-off decision on a root cause investigation's findings.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    rca = models.ForeignKey(
        RootCauseAnalysis,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rca_approvals",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    comments = models.TextField(
        blank=True,
        default="",
    )

    decided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = "Approval"
        verbose_name_plural = "Approvals"
        indexes = [
            models.Index(fields=["rca"]),
            models.Index(fields=["status"]),
            models.Index(fields=["approver"]),
        ]

    def __str__(self):
        return f"Approval[{self.pk}] - {self.get_status_display()}"
