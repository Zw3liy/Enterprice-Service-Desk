"""
Presentation-only template filters for the Enterprise Service Desk UI.

These helpers never touch field names, cleaned data or validation - they
only add HTML/ARIA attributes at render time.
"""

from django import template

register = template.Library()


@register.filter(name="esd_field")
def esd_field(bound_field):
    """Render a bound field with accessibility attributes wired up.

    Adds ``aria-invalid`` when the field has errors and ``aria-describedby``
    pointing at the help-text / error elements emitted by
    ``includes/form_fields.html``.
    """

    attrs = {}
    described_by = []

    if bound_field.help_text:
        described_by.append(f"{bound_field.auto_id}_help")

    if bound_field.errors:
        attrs["aria-invalid"] = "true"
        described_by.extend(
            f"{bound_field.auto_id}_error_{i}"
            for i in range(1, len(bound_field.errors) + 1)
        )

    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)

    if bound_field.field.required:
        attrs["aria-required"] = "true"

    return bound_field.as_widget(attrs=attrs)
