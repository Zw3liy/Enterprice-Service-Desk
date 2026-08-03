from django import forms


class NotificationPreferenceForm(forms.Form):
    email_enabled = forms.BooleanField(required=False, initial=True)
    in_app_enabled = forms.BooleanField(required=False, initial=True)
