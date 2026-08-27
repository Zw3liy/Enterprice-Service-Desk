from django import forms

from ..models import Supplier, Department


class SupplierCreateForm(forms.ModelForm):
    """
    Supplier create/update form for the Service Desk UI.

    When constructed with ``user=``, the department choices are
    narrowed to the departments that user actually manages, so the
    UI cannot offer an option the service layer will reject.
    """

    class Meta:
        model = Supplier
        fields = [
            "name",
            "description",
            "contact_name",
            "contact_email",
            "phone",
            "department",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Supplier name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional supplier details",
                }
            ),
            "contact_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Primary contact name",
                }
            ),
            "contact_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "contact@example.com",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+1 555 555 5555",
                }
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        self.fields["department"].queryset = self._department_choices(user)
        self.fields["department"].required = False
        self.fields["description"].required = False
        self.fields["contact_name"].required = False
        self.fields["contact_email"].required = False
        self.fields["phone"].required = False
        self.fields["is_active"].required = False

    @staticmethod
    def _department_choices(user):
        """
        Departments this user may file a supplier against.

        Administrators (and superusers) see every department;
        a Manager only sees the ones they manage. Anonymous or
        role-less callers get the full list — the service layer and
        the view mixins remain the authoritative gate, this is a
        usability narrowing, not the security boundary.
        """

        from apps.service_desk.security.policies import (
            is_administrator,
            is_manager,
        )

        if user is None or is_administrator(user):
            return Department.objects.all()

        if is_manager(user):
            return user.managed_departments.all()

        return Department.objects.all()


class SupplierUpdateForm(SupplierCreateForm):
    """
    Supplier update form.

    Identical field set to creation — kept as a distinct class so the
    two flows can diverge without a conditional inside a single form.
    """
