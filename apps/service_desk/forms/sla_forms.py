from django import forms

from ..models import Department, SLAPolicy


class SLAPolicyForm(forms.ModelForm):
    """
    SLA policy create/update form.

    Department choices are narrowed to what the acting user may
    actually write (Administrators: everything, including the
    organisation-wide default; Managers: their own departments only).
    The service layer re-checks this — the narrowing here is for
    usability, not security.
    """

    class Meta:
        model = SLAPolicy
        fields = [
            "name",
            "priority",
            "department",
            "response_minutes",
            "resolution_minutes",
            "warning_threshold_percent",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Urgent — IT",
                }
            ),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "response_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "resolution_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "warning_threshold_percent": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 99}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None or is_administrator(user):
            self.fields["department"].queryset = Department.objects.all()
            self.fields["department"].required = False
            self.fields["department"].help_text = (
                "Leave empty for the organisation-wide default for "
                "this priority."
            )
        elif is_manager(user):
            self.fields["department"].queryset = (
                user.managed_departments.all()
            )
            self.fields["department"].required = True
            self.fields["department"].empty_label = None
            self.fields["department"].help_text = (
                "Only administrators can create organisation-wide "
                "policies."
            )
        else:
            self.fields["department"].queryset = Department.objects.none()

        self.fields["is_active"].required = False
