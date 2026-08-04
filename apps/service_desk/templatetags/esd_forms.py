from django import template

register = template.Library()

@register.filter(name='add_aria_attrs')
def add_aria_attrs(field):
    """
    Dynamically injects Bootstrap classes and accessible ARIA attributes 
    into Django form field widgets based on their state and validation errors.
    """
    if not hasattr(field, 'as_widget'):
        return field

    existing_classes = field.field.widget.attrs.get('class', '')
    
    # Determine base form control class by widget type
    widget_type = field.field.widget.__class__.__name__.lower()
    if 'select' in widget_type:
        base_class = 'form-select esd-select'
    elif 'checkbox' in widget_type:
        base_class = 'form-check-input esd-checkbox'
    elif 'file' in widget_type:
        base_class = 'form-control esd-file-input'
    else:
        base_class = 'form-control esd-input'

    # Append validation error styling if field has errors
    if field.errors:
        base_class += ' is-invalid esd-input--invalid'

    # Combine classes cleanly without duplication
    classes = f"{base_class} {existing_classes}".strip()

    # Build accessibility attributes dict
    attrs = {
        'class': classes,
    }

    if field.errors:
        attrs['aria-invalid'] = 'true'
        attrs['aria-describedby'] = f"{field.id_for_label}_errors"
    elif field.help_text:
        attrs['aria-describedby'] = f"{field.id_for_label}_help"

    return field.as_widget(attrs=attrs)