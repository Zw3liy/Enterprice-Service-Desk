from django import forms

from ..models import Ticket, Department, RequestType


class TicketCreateForm(forms.ModelForm):
    """
    Clean production-ready ticket creation form.
    Matches the current Ticket model exactly.
    """

    class Meta:
        model = Ticket
        fields = [
            "title",
            "description",
            "priority",
            "urgency",
            "department",
            "request_type",
            "tags",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter ticket title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Describe the issue",
                }
            ),
            "priority": forms.Select(
                attrs={"class": "form-select"}
            ),
            "urgency": forms.Select(
                attrs={"class": "form-select"}
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
            "request_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "tags": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "network,vpn,printer",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].queryset = Department.objects.all()
        self.fields["request_type"].queryset = RequestType.objects.all()

        self.fields["department"].required = False
        self.fields["request_type"].required = False
        self.fields["tags"].required = False