from django import forms

from ..models import Department, Release


class ReleaseCreateForm(forms.ModelForm):
    """
    Release creation form.

    ``status``, ``owner`` and ``changes`` are deliberately excluded —
    owner defaults to the creator (``ReleaseService.create_release``),
    changes are linked afterwards through the eligibility-checked
    ``link_change`` service call, never accepted as raw create-time
    input (mass-assignment prevention).
    """

    class Meta:
        model = Release
        fields = [
            "name",
            "version",
            "environment",
            "department",
            "deployment_plan",
            "validation_plan",
            "rollback_plan",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "version": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "2026.09.1"}
            ),
            "environment": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "deployment_plan": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "validation_plan": forms.Textarea(
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
        self.fields["deployment_plan"].required = False
        self.fields["validation_plan"].required = False
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


class ReleaseScheduleForm(forms.Form):
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
