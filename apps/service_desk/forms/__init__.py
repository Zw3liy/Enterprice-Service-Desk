"""HTML forms for the Service Desk UI."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.service_desk.models import (
    Asset,
    Category,
    Company,
    CustomerFeedback,
    Department,
    KnowledgeArticle,
    Priority,
    Queue,
    RequestType,
    Status,
    Ticket,
    TicketComment,
    WorkLog,
)

User = get_user_model()


class StyledFormMixin:
    def _style(self) -> None:
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = f"{css} form-check-input".strip()
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"{css} form-select".strip()
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs["class"] = f"{css} form-control".strip()
            else:
                field.widget.attrs["class"] = f"{css} form-control".strip()


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields["username"].widget.attrs["placeholder"] = "Username"
        self.fields["password"].widget.attrs["placeholder"] = "Password"


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class TicketCreateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "title",
            "description",
            "ticket_type",
            "channel",
            "department",
            "request_type",
            "category",
            "priority",
            "queue",
            "impact",
            "urgency",
            "tags",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "tags": forms.TextInput(attrs={"placeholder": "comma,separated,tags"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self._style()
        if company is not None:
            self.fields["department"].queryset = Department.objects.filter(
                company=company, is_active=True
            )
            self.fields["request_type"].queryset = RequestType.objects.filter(
                department__company=company, is_active=True
            )
            self.fields["category"].queryset = Category.objects.filter(
                company=company, is_active=True
            )
            self.fields["priority"].queryset = Priority.objects.filter(
                company=company, is_active=True
            )
            self.fields["queue"].queryset = Queue.objects.filter(
                company=company, is_active=True
            )
        for optional in ("request_type", "category", "priority", "queue", "department"):
            self.fields[optional].required = False

    def clean_tags(self):
        tags = self.cleaned_data.get("tags")
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        return tags or []


class TicketUpdateForm(TicketCreateForm):
    class Meta(TicketCreateForm.Meta):
        fields = TicketCreateForm.Meta.fields + [
            "status",
            "assignee",
            "is_major_incident",
        ]

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, company=company, **kwargs)
        if company is not None:
            self.fields["status"].queryset = Status.objects.filter(
                company=company, is_active=True
            )
        self.fields["assignee"].queryset = User.objects.filter(is_active=True).order_by(
            "username"
        )
        self.fields["assignee"].required = False
        self.fields["status"].required = False


class TicketFilterForm(StyledFormMixin, forms.Form):
    q = forms.CharField(required=False, label="Search")
    status = forms.ModelChoiceField(queryset=Status.objects.none(), required=False)
    priority = forms.ModelChoiceField(queryset=Priority.objects.none(), required=False)
    queue = forms.ModelChoiceField(queryset=Queue.objects.none(), required=False)
    ticket_type = forms.ChoiceField(
        choices=[("", "All types")] + list(Ticket.TicketType.choices), required=False
    )
    open_only = forms.BooleanField(required=False, initial=True, label="Open only")
    mine = forms.BooleanField(required=False, label="My tickets")

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        if company is not None:
            self.fields["status"].queryset = Status.objects.filter(company=company)
            self.fields["priority"].queryset = Priority.objects.filter(company=company)
            self.fields["queue"].queryset = Queue.objects.filter(company=company)


class CommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["body", "is_internal"]
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Add a comment…"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class WorkLogForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = WorkLog
        fields = ["description", "minutes_spent", "is_billable"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class AttachmentForm(StyledFormMixin, forms.Form):
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class AssignForm(StyledFormMixin, forms.Form):
    assignee = forms.ModelChoiceField(queryset=User.objects.none(), required=False)
    queue = forms.ModelChoiceField(queryset=Queue.objects.none(), required=False)
    note = forms.CharField(required=False, max_length=255)
    auto_assign = forms.BooleanField(required=False, label="Auto-assign least loaded agent")

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields["assignee"].queryset = User.objects.filter(is_active=True).order_by(
            "username"
        )
        if company is not None:
            self.fields["queue"].queryset = Queue.objects.filter(
                company=company, is_active=True
            )


class KnowledgeArticleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = KnowledgeArticle
        fields = [
            "title",
            "summary",
            "body",
            "category",
            "is_published",
            "is_internal",
            "tags",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 2}),
            "body": forms.Textarea(attrs={"rows": 12}),
            "tags": forms.TextInput(attrs={"placeholder": "comma,separated,tags"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self._style()
        if company is not None:
            self.fields["category"].queryset = Category.objects.filter(company=company)

    def clean_tags(self):
        tags = self.cleaned_data.get("tags")
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        return tags or []


class AssetForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "name",
            "asset_tag",
            "asset_type",
            "lifecycle_state",
            "serial_number",
            "manufacturer",
            "model_name",
            "location",
            "department",
            "is_active",
            "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self._style()
        if company is not None:
            self.fields["department"].queryset = Department.objects.filter(company=company)


class FeedbackForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerFeedback
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class CompanyBootstrapForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "slug", "primary_email", "timezone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
