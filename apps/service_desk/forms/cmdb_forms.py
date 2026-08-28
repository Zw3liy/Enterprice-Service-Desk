from django import forms

from ..models import ConfigurationItem, ConfigurationItemType, Department


class ConfigurationItemForm(forms.ModelForm):
    """
    CI create/update form.

    When constructed with ``user=``, ``department`` choices are
    narrowed to departments that user manages — the service layer
    (``CMDBService.assert_department_allowed``) remains the real
    boundary, this is a usability narrowing only.
    """

    class Meta:
        model = ConfigurationItem
        fields = [
            "ci_type",
            "name",
            "identifier",
            "status",
            "criticality",
            "department",
            "owner",
            "description",
        ]

        widgets = {
            "ci_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "identifier": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Asset tag / serial"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "criticality": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["ci_type"].queryset = ConfigurationItemType.objects.filter(
            is_active=True
        )
        self.fields["department"].queryset = self._department_choices(user)
        self.fields["department"].required = False
        self.fields["owner"].required = False
        self.fields["description"].required = False

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
