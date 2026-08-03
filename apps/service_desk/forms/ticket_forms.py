"""
Enterprise Service Desk - Ticket forms.

The widgets defined here carry the design-system CSS classes used by the
"New Support Ticket" page. Only widgets/labels/help text are styled - the
underlying field names map 1:1 onto the existing ``Ticket`` model, so all
validation and persistence behaviour is unchanged.
"""

from django import forms

from ..models import Department, RequestType, Ticket


# Shared widget class strings (see static/css/enterprise.css)
INPUT_CLASS = "esd-input"
SELECT_CLASS = "esd-input esd-select"
TEXTAREA_CLASS = "esd-input esd-textarea"


PRIORITY_CHOICES = [
    ("low", "Low - minor inconvenience"),
    ("normal", "Normal - standard request"),
    ("high", "High - work is blocked"),
    ("urgent", "Urgent - business critical"),
]


class TicketCreateForm(forms.ModelForm):
    """Create a support ticket.

    ``requester_name``, ``work_email`` and ``priority`` are not columns on the
    ``Ticket`` model; they are persisted into the existing
    ``custom_field_values`` JSON field so that no schema change is required.
    """

    requester_name = forms.CharField(
        label="Your name",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Jane Ndlovu",
                "autocomplete": "name",
            }
        ),
    )

    work_email = forms.EmailField(
        label="Work email",
        widget=forms.EmailInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "jane.ndlovu@company.com",
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
        help_text="We send status updates to this address.",
    )

    priority = forms.ChoiceField(
        label="Priority",
        choices=PRIORITY_CHOICES,
        initial="normal",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )

    class Meta:
        model = Ticket
        fields = [
            "department",
            "request_type",
            "title",
            "description",
        ]
        labels = {
            "department": "Department",
            "request_type": "Category",
            "title": "Issue title",
            "description": "Description / details",
        }
        help_texts = {
            "title": "One short line, e.g. \"Laptop will not connect to VPN\".",
            "description": (
                "Steps you took, what you expected, what happened instead, "
                "and any error messages."
            ),
        }
        widgets = {
            "department": forms.Select(attrs={"class": SELECT_CLASS}),
            "request_type": forms.Select(attrs={"class": SELECT_CLASS}),
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Briefly, what is wrong?",
                    "maxlength": 200,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 8,
                    "placeholder": (
                        "Tell us what happened, when it started, and who is "
                        "affected."
                    ),
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["department"].queryset = Department.objects.all()
        self.fields["department"].empty_label = "Select a department"

        self.fields["request_type"].queryset = RequestType.objects.filter(
            is_active=True
        ).select_related("department")
        self.fields["request_type"].empty_label = "Select a category"

        # Field order drives the fallback rendering loop in the template.
        self.order_fields(
            [
                "requester_name",
                "work_email",
                "department",
                "request_type",
                "priority",
                "title",
                "description",
            ]
        )

        if user is not None and user.is_authenticated and not self.is_bound:
            self.fields["requester_name"].initial = (
                user.get_full_name() or user.get_username()
            )
            self.fields["work_email"].initial = user.email

        # Mark required fields for the accessible template rendering.
        for field in self.fields.values():
            if field.required:
                field.widget.attrs.setdefault("required", "required")

    def save(self, commit=True):
        ticket = super().save(commit=False)

        if self.user is not None and self.user.is_authenticated:
            ticket.requester = self.user

        values = dict(ticket.custom_field_values or {})
        values.update(
            {
                "requester_name": self.cleaned_data["requester_name"],
                "work_email": self.cleaned_data["work_email"],
                "priority": self.cleaned_data["priority"],
            }
        )
        ticket.custom_field_values = values

        if commit:
            ticket.save()
        return ticket
