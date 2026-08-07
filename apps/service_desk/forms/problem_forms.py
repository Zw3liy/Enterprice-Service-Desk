from django import forms

from ..models import Problem, Department


class ProblemCreateForm(forms.ModelForm):
    """
    Problem creation form.

    Mirrors TicketCreateForm's structure. Status, is_known_error,
    root_cause, and workaround are not user-set at creation time —
    they're managed through ProblemService's dedicated workflow
    methods once the problem exists.
    """

    class Meta:
        model = Problem
        fields = [
            "title",
            "description",
            "priority",
            "department",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter problem title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Describe the underlying problem",
                }
            ),
            "priority": forms.Select(
                attrs={"class": "form-select"}
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].queryset = Department.objects.all()
        self.fields["department"].required = False
