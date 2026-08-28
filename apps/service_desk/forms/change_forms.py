from django import forms

from ..models import Change, Department


class ChangeCreateForm(forms.ModelForm):
    """
    Change creation form.

    ``status``, ``assigned_to``, ``impact``/``urgency``/``risk_level``
    are deliberately excluded — they are set through
    ``ChangeService`` transitions (assessment, assignment), never
    accepted as raw create-time input (mass-assignment prevention).
    """

    class Meta:
        model = Change
        fields = [
            "title",
            "description",
            "change_type",
            "department",
            "implementation_plan",
            "test_plan",
            "rollback_plan",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Change title"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "change_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
            "implementation_plan": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "test_plan": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "rollback_plan": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].queryset = self._department_choices(user)
        self.fields["department"].required = False
        self.fields["implementation_plan"].required = False
        self.fields["test_plan"].required = False
        self.fields["rollback_plan"].required = False

    @staticmethod
    def _department_choices(user):
        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None or is_administrator(user):
            return Department.objects.all()

        if is_manager(user):
            return user.managed_departments.all()

        return Department.objects.all()


class ChangeAssessmentForm(forms.Form):
    impact = forms.ChoiceField(
        choices=Change.IMPACT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    urgency = forms.ChoiceField(
        choices=Change.URGENCY_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class ChangeScheduleForm(forms.Form):
    scheduled_start = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
    )
    scheduled_end = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
    )
