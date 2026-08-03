from django import forms

from apps.service_desk.models import SLA


class SLAForm(forms.ModelForm):
    class Meta:
        model = SLA
        fields = [
            "name",
            "priority",
            "response_minutes",
            "resolution_minutes",
            "business_hours_only",
            "is_active",
            "description",
        ]
