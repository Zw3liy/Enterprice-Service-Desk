from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.text import slugify

from apps.form_builder.models import FormDefinition, FormSubmission
from apps.service_desk.services.ticket_service import TicketService


class FormBuilderService:
    SUPPORTED_TYPES = {
        "text",
        "textarea",
        "number",
        "dropdown",
        "multiselect",
        "date",
        "boolean",
        "email",
        "url",
    }

    @classmethod
    def create_form(
        cls,
        company,
        *,
        name: str,
        code: str = "",
        schema: list | None = None,
        request_type=None,
        description: str = "",
    ) -> FormDefinition:
        schema = schema or []
        cls.validate_schema(schema)
        return FormDefinition.objects.create(
            company=company,
            name=name,
            code=code or slugify(name)[:60],
            description=description,
            request_type=request_type,
            schema=schema,
        )

    @classmethod
    def validate_schema(cls, schema: list) -> None:
        if not isinstance(schema, list):
            raise ValidationError("schema must be a list")
        names = set()
        for field in schema:
            if not isinstance(field, dict):
                raise ValidationError("each field must be an object")
            name = field.get("name")
            ftype = field.get("type") or field.get("field_type")
            if not name:
                raise ValidationError("field.name is required")
            if name in names:
                raise ValidationError(f"duplicate field name: {name}")
            names.add(name)
            if ftype not in cls.SUPPORTED_TYPES:
                raise ValidationError(f"unsupported field type: {ftype}")
            if ftype in {"dropdown", "multiselect"} and not field.get("options"):
                raise ValidationError(f"{name} requires options")

    @classmethod
    def validate_values(cls, form: FormDefinition, values: dict) -> dict:
        values = values or {}
        errors = {}
        for field in form.schema or []:
            name = field.get("name")
            label = field.get("label") or name
            required = bool(field.get("required") or field.get("is_required"))
            ftype = field.get("type") or field.get("field_type")
            raw = values.get(name)
            if required and (raw is None or raw == "" or raw == []):
                errors[name] = f"{label} is required"
                continue
            if raw in (None, ""):
                continue
            if ftype == "number":
                try:
                    float(raw)
                except (TypeError, ValueError):
                    errors[name] = f"{label} must be a number"
            elif ftype == "dropdown":
                options = [str(o) for o in field.get("options") or []]
                if str(raw) not in options:
                    errors[name] = f"{label} has invalid choice"
            elif ftype == "multiselect":
                options = {str(o) for o in field.get("options") or []}
                selected = raw if isinstance(raw, list) else [raw]
                if any(str(s) not in options for s in selected):
                    errors[name] = f"{label} has invalid choices"
            elif ftype == "boolean" and not isinstance(raw, bool) and str(raw).lower() not in {
                "true",
                "false",
                "1",
                "0",
                "yes",
                "no",
            }:
                errors[name] = f"{label} must be boolean"
        if errors:
            raise ValidationError(errors)
        return values

    @classmethod
    def submit(
        cls,
        form: FormDefinition,
        values: dict,
        *,
        user=None,
        create_ticket: bool = True,
        title: str = "",
    ) -> FormSubmission:
        cleaned = cls.validate_values(form, values)
        ticket = None
        if create_ticket:
            ticket = TicketService.create_ticket(
                title=title or f"Form: {form.name}",
                description="\n".join(f"{k}: {v}" for k, v in cleaned.items()),
                company=form.company,
                request_type=form.request_type,
                department=getattr(form.request_type, "department", None),
                custom_field_values=cleaned,
                requester_user=user,
                actor=user,
                channel="portal",
                run_ai=False,
            )
        return FormSubmission.objects.create(
            form=form,
            company=form.company,
            values=cleaned,
            submitted_by=user,
            ticket=ticket,
        )
