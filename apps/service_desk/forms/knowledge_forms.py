from django import forms

from ..models import KnowledgeArticle, KnowledgeCategory


class KnowledgeArticleForm(forms.ModelForm):
    """
    Knowledge article create/update form.

    ``author``, ``reviewer``, ``status``, ``version`` and
    ``published_at`` are deliberately excluded — they are set through
    ``KnowledgeService`` (author defaults to the creator; the rest
    move only through workflow transitions), never accepted as raw
    input (mass-assignment prevention).
    """

    class Meta:
        model = KnowledgeArticle
        fields = [
            "category",
            "title",
            "content",
            "tags",
            "visibility",
        ]

        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(
                attrs={"class": "form-control", "rows": 10}
            ),
            "tags": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "comma, separated, tags",
                }
            ),
            "visibility": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = KnowledgeCategory.objects.filter(
            is_active=True
        )
        self.fields["tags"].required = False
