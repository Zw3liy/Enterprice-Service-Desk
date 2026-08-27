"""
Root Cause Analysis authoring forms.

These back the Problem detail page's RCA panels. They exist so the
five previously read-only RCA models (FiveWhys, FishboneFactor,
Evidence, Action, Approval) can be authored through accessible,
validated, CSRF-protected HTML forms instead of the Django admin.

Each form validates *shape* only. Business rules — whether the RCA is
still open, who may approve, which action transitions are legal —
live in ProblemService and are re-checked there.
"""

from django import forms
from django.contrib.auth import get_user_model

from ..models import Action, Approval, Evidence, FishboneFactor, RootCauseAnalysis

User = get_user_model()


class RCADetailsForm(forms.ModelForm):
    """
    The RCA's own narrative fields.
    """

    class Meta:
        model = RootCauseAnalysis
        fields = [
            "method",
            "problem_statement",
            "trigger_event",
            "contributing_factors",
            "mitigation_steps",
            "preventative_measures",
        ]

        widgets = {
            "method": forms.Select(attrs={"class": "form-select"}),
            "problem_statement": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "trigger_event": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "contributing_factors": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "mitigation_steps": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "preventative_measures": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in (
            "trigger_event",
            "contributing_factors",
            "mitigation_steps",
            "preventative_measures",
        ):
            self.fields[name].required = False


class FiveWhysStepForm(forms.Form):
    """
    One "why" in the chain. The step number is allocated by the
    service, never submitted by the browser.
    """

    question = forms.CharField(
        label="Why?",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Why did this happen?",
            }
        ),
    )

    answer = forms.CharField(
        label="Because",
        widget=forms.Textarea(
            attrs={"class": "form-control form-control-sm", "rows": 2}
        ),
    )


class FishboneFactorForm(forms.ModelForm):

    class Meta:
        model = FishboneFactor
        fields = ["category", "factor_description", "is_root_cause"]

        widgets = {
            "category": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "factor_description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "is_root_cause": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_root_cause"].required = False


class EvidenceForm(forms.ModelForm):

    class Meta:
        model = Evidence
        fields = ["title", "file_or_link", "description"]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "file_or_link": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "URL or attachment reference",
                }
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False


class ActionForm(forms.ModelForm):
    """
    Corrective / preventive action (CAPA).
    """

    class Meta:
        model = Action
        fields = ["action_type", "description", "assigned_to", "due_date"]

        widgets = {
            "action_type": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "assigned_to": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "due_date": forms.DateInput(
                attrs={"class": "form-control form-control-sm", "type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Actions are worked by staff, so the pool is users who can
        # actually change a problem — not every account on the system.
        self.fields["assigned_to"].queryset = (
            User.objects.filter(is_active=True)
            .filter(
                models_q()
            )
            .distinct()
            .order_by("username")
        )
        self.fields["assigned_to"].required = False


def models_q():
    """
    Users holding change_problem, directly or through a group.
    """

    from django.db.models import Q

    return Q(
        groups__permissions__codename="change_problem"
    ) | Q(
        user_permissions__codename="change_problem"
    ) | Q(is_superuser=True)


class ApprovalRequestForm(forms.Form):
    """
    Nominate somebody to sign the investigation off.
    """

    approver = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["approver"].queryset = (
            User.objects.filter(is_active=True)
            .filter(models_q())
            .distinct()
            .order_by("username")
        )


class ApprovalDecisionForm(forms.Form):

    DECISION_CHOICES = [
        ("approved", "Approve"),
        ("rejected", "Reject"),
    ]

    status = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control form-control-sm", "rows": 2}
        ),
    )
