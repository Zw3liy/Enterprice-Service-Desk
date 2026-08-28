from django import forms

from ..models import CatalogItem, Department, ServiceCategory


class CatalogItemForm(forms.ModelForm):
    """
    Catalogue item create/update form.

    When constructed with ``user=``, ``fulfillment_department``
    choices are narrowed to the departments that user actually
    manages, so the UI cannot offer an option the service layer will
    reject. The service layer (``CatalogService.assert_department_
    allowed``) remains the real boundary — this is a usability
    narrowing only.
    """

    class Meta:
        model = CatalogItem
        fields = [
            "category",
            "name",
            "description",
            "fulfillment_department",
            "requires_approval",
            "default_priority",
            "expected_delivery_days",
            "is_active",
        ]

        widgets = {
            "category": forms.Select(
                attrs={"class": "form-select"}
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Item name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "What this item is and how to use it",
                }
            ),
            "fulfillment_department": forms.Select(
                attrs={"class": "form-select"}
            ),
            "requires_approval": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "default_priority": forms.Select(
                attrs={"class": "form-select"}
            ),
            "expected_delivery_days": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        self.fields["category"].queryset = ServiceCategory.objects.filter(
            is_active=True
        )
        self.fields["fulfillment_department"].queryset = (
            self._department_choices(user)
        )
        self.fields["fulfillment_department"].required = False
        self.fields["description"].required = False
        self.fields["expected_delivery_days"].required = False
        self.fields["is_active"].required = False

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


class ServiceRequestCreateForm(forms.Form):
    """
    The requester-facing form for submitting a service request
    against one already-chosen ``CatalogItem`` (the item itself is
    bound from the URL, not offered as a form field — see
    ``ServiceRequestCreateView``).
    """

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": 1}
        ),
    )

    justification = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Why do you need this? (optional)",
            }
        ),
    )
