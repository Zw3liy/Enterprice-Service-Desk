"""Validation helpers for dynamic custom fields on request types."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


def validate_custom_fields(request_type, values: dict[str, Any] | None) -> dict[str, str]:
    """
    Validate submitted custom field values against the request type schema.

    Returns a dict of field_name -> error message (empty if valid).
    """
    values = values or {}
    errors: dict[str, str] = {}

    if request_type is None:
        return errors

    fields = list(request_type.custom_fields.all())
    for field in fields:
        raw = values.get(field.name, values.get(field.label or "", None))
        label = field.label or field.name

        if field.is_required and _is_empty(raw):
            errors[field.name] = f"{label} is required."
            continue

        if _is_empty(raw):
            continue

        field_type = field.field_type
        if field_type == "number":
            try:
                float(raw)
            except (TypeError, ValueError):
                errors[field.name] = f"{label} must be a number."
        elif field_type == "boolean":
            if not isinstance(raw, bool) and str(raw).lower() not in {
                "1",
                "0",
                "true",
                "false",
                "yes",
                "no",
                "on",
                "off",
            }:
                errors[field.name] = f"{label} must be true or false."
        elif field_type == "dropdown":
            options = [str(o) for o in (field.options or [])]
            if str(raw) not in options:
                errors[field.name] = f"{label} must be one of: {', '.join(options)}."
        elif field_type == "multiselect":
            options = {str(o) for o in (field.options or [])}
            selected = raw if isinstance(raw, (list, tuple)) else [raw]
            invalid = [str(s) for s in selected if str(s) not in options]
            if invalid:
                errors[field.name] = f"{label} has invalid choices: {', '.join(invalid)}."
        elif field_type == "date":
            if not _is_date(raw):
                errors[field.name] = f"{label} must be a valid date (YYYY-MM-DD)."
        elif field_type == "datetime":
            if not _is_datetime(raw):
                errors[field.name] = f"{label} must be a valid date/time."
        elif field_type == "email":
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(raw)):
                errors[field.name] = f"{label} must be a valid email."
        elif field_type == "url":
            if not re.match(r"^https?://", str(raw), re.I):
                errors[field.name] = f"{label} must be an http(s) URL."

        if field.validation_regex and not errors.get(field.name):
            try:
                if not re.search(field.validation_regex, str(raw)):
                    errors[field.name] = f"{label} format is invalid."
            except re.error:
                errors[field.name] = f"{label} has an invalid validation pattern."

    return errors


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        return True
    return False


def _is_date(value: Any) -> bool:
    if isinstance(value, date) and not isinstance(value, datetime):
        return True
    try:
        datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _is_datetime(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    text = str(value).replace("Z", "+00:00")
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        return _is_date(value)
