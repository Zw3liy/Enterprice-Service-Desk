"""
Ticket forms.

Server-side validation for creation: active master data only, RBAC-scoped
department choices, tag normalisation, and optional initial attachment.
"""

from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError

from apps.service_desk.models import Department, RequestType, Ticket, TicketAttachment
from apps.service_desk.security.policies import is_administrator


def normalize_tags(raw: str) -> str:
    """
    Collapse a free-text tag string into a stable, comma-separated form.

    Rules:
    - split on commas or whitespace
    - lowercase
    - strip punctuation noise at the edges
    - drop empties and duplicates (order-preserving)
    - cap total length to the model field
    """

    if not raw:
        return ""

    parts = re.split(r"[,;\s]+", raw.strip())
    seen: set[str] = set()
    cleaned: list[str] = []

    for part in parts:
        tag = re.sub(r"^[^a-zA-Z0-9_+#.-]+|[^a-zA-Z0-9_+#.-]+$", "", part)
        tag = tag.lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        cleaned.append(tag)

    result = ",".join(cleaned)
    return result[:255]


def sanitize_attachment_filename(name: str) -> str:
    """
    Strip path components and control characters from an uploaded filename.
    """

    if not name:
        return "attachment"

    # Drop any directory components (Unix or Windows).
    name = name.replace("\\", "/").split("/")[-1]
    # Remove nulls and other control characters.
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # Collapse runs of whitespace.
    name = re.sub(r"\s+", " ", name).strip()
    # Refuse path-traversal residue and empty results.
    name = name.replace("..", ".")
    if not name or name in {".", ".."}:
        return "attachment"
    return name[:255]


def _attachment_accept_attr() -> str:
    return ",".join(
        f".{ext}" for ext in sorted(TicketAttachment.ALLOWED_EXTENSIONS)
    )


class TicketCreateForm(forms.ModelForm):
    """
    Production ticket creation form.

    Matches the live Ticket model. Department and request-type querysets
    are scoped in ``__init__`` from the acting user so a client cannot
    submit an out-of-scope department id.
    """

    attachment = forms.FileField(
        required=False,
        help_text=(
            "Optional supporting file "
            f"(max {TicketAttachment.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)."
        ),
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": _attachment_accept_attr(),
            }
        ),
    )

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
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Describe the issue",
                }
            ),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "urgency": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "request_type": forms.Select(attrs={"class": "form-select"}),
            "tags": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "network, vpn, printer",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        # Active request types only — inactive master data must never
        # appear as a selectable choice.
        active_types = RequestType.objects.filter(is_active=True).order_by(
            "name"
        )
        self.fields["request_type"].queryset = active_types
        self.fields["request_type"].required = True
        self.fields["request_type"].empty_label = (
            "---------" if active_types.exists() else "No active request types"
        )

        self.fields["department"].queryset = self._departments_for(user)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "---------"

        self.fields["tags"].required = False
        self.fields["title"].required = True
        self.fields["description"].required = True
        self.fields["priority"].required = True
        self.fields["urgency"].required = True

        # Surface empty-master-data state to the template without a
        # second query in the view.
        self.no_active_request_types = not active_types.exists()
        self.no_departments = not self.fields["department"].queryset.exists()

        if self.no_active_request_types:
            self.fields["request_type"].disabled = True
        if self.no_departments:
            self.fields["department"].disabled = True

    @staticmethod
    def _departments_for(user):
        """
        Department choices the acting user may target.

        Administrator: every department.
        Everyone else: every department (filing a request *to* a
        department is not the same as managing it). Object-level
        visibility after creation is still enforced by
        ``get_ticket_queryset``. An empty table yields an empty selector.
        """

        base = Department.objects.all().order_by("name")

        if user is None or not getattr(user, "is_authenticated", False):
            return base.none()

        # is_administrator short-circuit is intentional documentation of
        # the admin path; the queryset is the same for all authenticated
        # roles under the current data model.
        if is_administrator(user) or user.is_authenticated:
            return base

        return base.none()

    # ------------------------------------------------------------------
    # Field cleaners
    # ------------------------------------------------------------------

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise ValidationError("Title is required.")
        if len(title) < 3:
            raise ValidationError("Title must be at least 3 characters.")
        return title

    def clean_description(self):
        description = (self.cleaned_data.get("description") or "").strip()
        if not description:
            raise ValidationError("Description is required.")
        if len(description) < 10:
            raise ValidationError(
                "Description must be at least 10 characters."
            )
        return description

    def clean_priority(self):
        priority = self.cleaned_data.get("priority")
        valid = {value for value, _ in Ticket.PRIORITY_CHOICES}
        if priority not in valid:
            raise ValidationError("Select a valid priority.")
        return priority

    def clean_urgency(self):
        urgency = self.cleaned_data.get("urgency")
        valid = {value for value, _ in Ticket.URGENCY_CHOICES}
        if urgency not in valid:
            raise ValidationError("Select a valid urgency.")
        return urgency

    def clean_tags(self):
        return normalize_tags(self.cleaned_data.get("tags") or "")

    def clean_request_type(self):
        request_type = self.cleaned_data.get("request_type")
        if request_type is None:
            raise ValidationError("Select a request type.")
        if not request_type.is_active:
            raise ValidationError(
                "The selected request type is inactive and cannot be used."
            )
        return request_type

    def clean_department(self):
        department = self.cleaned_data.get("department")
        if department is None:
            return department

        allowed = self.fields["department"].queryset
        if not allowed.filter(pk=department.pk).exists():
            raise ValidationError(
                "You are not allowed to create tickets for that department."
            )
        return department

    def clean_attachment(self):
        uploaded = self.cleaned_data.get("attachment")
        if not uploaded:
            return None

        filename = sanitize_attachment_filename(
            getattr(uploaded, "name", "") or ""
        )
        uploaded.name = filename

        if "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()
        else:
            ext = ""

        if ext not in TicketAttachment.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(TicketAttachment.ALLOWED_EXTENSIONS))
            raise ValidationError(
                f"File extension '.{ext}' is not allowed. "
                f"Allowed extensions: {allowed}"
            )

        size = getattr(uploaded, "size", None)
        if size is None:
            uploaded.seek(0, 2)
            size = uploaded.tell()
            uploaded.seek(0)

        if size > TicketAttachment.MAX_FILE_SIZE_BYTES:
            max_mb = TicketAttachment.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValidationError(
                f"File size exceeds the {max_mb} MB limit."
            )

        return uploaded

    def clean(self):
        cleaned = super().clean()

        # Block submission entirely when master data is missing so the
        # user gets a clear, accessible error instead of a silent empty
        # foreign key.
        if self.no_active_request_types:
            raise ValidationError(
                "No active request types are configured. "
                "Contact an administrator before opening a ticket."
            )

        # Ownership / assignment / lifecycle fields are never taken from
        # the client. ModelForm only binds declared fields, and the view
        # re-filters cleaned_data before calling TicketService, so a
        # crafted POST that includes these keys is silently ignored
        # rather than treated as a form error (which would leak that the
        # field names are meaningful).

        return cleaned
