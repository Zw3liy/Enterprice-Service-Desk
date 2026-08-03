from django import forms

from .models import Ticket


class TicketForm(forms.ModelForm):

    class Meta:

        model = Ticket

        fields = (
            "subject",
            "description",
            "category",
            "priority",
            "assigned_to",
        )

        widgets = {

            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter ticket subject",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Describe the issue...",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "assigned_to": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

        }

        labels = {

            "subject": "Subject",

            "description": "Description",

            "category": "Category",

            "priority": "Priority",

            "assigned_to": "Assigned To",

        }

    def clean_subject(self):

        subject = self.cleaned_data["subject"].strip()

        if len(subject) < 5:

            raise forms.ValidationError(
                "Subject must be at least 5 characters long."
            )

        return subject

    def clean_description(self):

        description = self.cleaned_data["description"].strip()

        if len(description) < 10:

            raise forms.ValidationError(
                "Description must be at least 10 characters long."
            )

        return description


class TicketUpdateForm(forms.ModelForm):

    class Meta:

        model = Ticket

        fields = (
            "status",
            "priority",
            "assigned_to",
            "resolved_at",
        )

        widgets = {

            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "assigned_to": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "resolved_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),

        }

        labels = {

            "status": "Status",

            "priority": "Priority",

            "assigned_to": "Assigned To",

            "resolved_at": "Resolved At",

        }