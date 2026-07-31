"""Dynamic Django form factory driven by CustomField definitions."""

from __future__ import annotations

from django import forms


def build_dynamic_form(request_type, data=None, files=None, initial=None):
    """
    Build a form class instance for the custom fields on a request type.
    """
    fields: dict = {}

    if request_type is None:
        return type("EmptyDynamicForm", (forms.Form,), {})(data=data, files=files, initial=initial)

    for custom in request_type.custom_fields.all().order_by("sort_order", "name"):
        label = custom.label or custom.name
        required = custom.is_required
        help_text = custom.help_text or ""
        widget_attrs = {"class": "form-control", "data-field": custom.name}

        if custom.field_type == "text":
            field = forms.CharField(
                label=label, required=required, help_text=help_text,
                widget=forms.TextInput(attrs=widget_attrs),
            )
        elif custom.field_type == "textarea":
            field = forms.CharField(
                label=label, required=required, help_text=help_text,
                widget=forms.Textarea(attrs={**widget_attrs, "rows": 3}),
            )
        elif custom.field_type == "number":
            field = forms.FloatField(
                label=label, required=required, help_text=help_text,
                widget=forms.NumberInput(attrs=widget_attrs),
            )
        elif custom.field_type == "dropdown":
            choices = [("", "---------")] + [(str(o), str(o)) for o in (custom.options or [])]
            field = forms.ChoiceField(
                label=label, required=required, help_text=help_text, choices=choices,
                widget=forms.Select(attrs={**widget_attrs, "class": "form-select"}),
            )
        elif custom.field_type == "multiselect":
            choices = [(str(o), str(o)) for o in (custom.options or [])]
            field = forms.MultipleChoiceField(
                label=label, required=required, help_text=help_text, choices=choices,
                widget=forms.SelectMultiple(attrs={**widget_attrs, "class": "form-select"}),
            )
        elif custom.field_type == "date":
            field = forms.DateField(
                label=label, required=required, help_text=help_text,
                widget=forms.DateInput(attrs={**widget_attrs, "type": "date"}),
            )
        elif custom.field_type == "datetime":
            field = forms.DateTimeField(
                label=label, required=required, help_text=help_text,
                widget=forms.DateTimeInput(attrs={**widget_attrs, "type": "datetime-local"}),
            )
        elif custom.field_type == "boolean":
            field = forms.BooleanField(
                label=label, required=False, help_text=help_text,
                widget=forms.CheckboxInput(attrs={"class": "form-check-input", "data-field": custom.name}),
            )
        elif custom.field_type == "email":
            field = forms.EmailField(
                label=label, required=required, help_text=help_text,
                widget=forms.EmailInput(attrs=widget_attrs),
            )
        elif custom.field_type == "url":
            field = forms.URLField(
                label=label, required=required, help_text=help_text,
                widget=forms.URLInput(attrs=widget_attrs),
            )
        else:
            field = forms.CharField(
                label=label, required=required, help_text=help_text,
                widget=forms.TextInput(attrs=widget_attrs),
            )

        fields[custom.name] = field

    form_class = type("DynamicTicketForm", (forms.Form,), fields)
    return form_class(data=data, files=files, initial=initial)
