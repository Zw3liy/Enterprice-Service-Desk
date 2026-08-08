from django import forms
from apps.service_desk.models.sla_policy import SLAPolicy


class SLAPolicyForm(forms.ModelForm):
    class Meta:
        model = SLAPolicy
        fields = ['name', 'duration_minutes', 'description']

    def clean_duration_minutes(self):
        duration = self.cleaned_data.get('duration_minutes')
        if duration <= 0:
            raise forms.ValidationError("Duration must be greater than zero minutes.")
        return duration
