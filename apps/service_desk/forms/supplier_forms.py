from django import forms

from ..models import Supplier, Department


class SupplierCreateForm(forms.ModelForm):
    """
    Supplier creation form for the Service Desk UI.
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].queryset = Department.objects.all()
        self.fields["department"].required = False
        self.fields["description"].required = False
        self.fields["contact_name"].required = False
        self.fields["contact_email"].required = False
        self.fields["phone"].required = False
        self.fields["is_active"].required = False
