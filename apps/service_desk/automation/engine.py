"""Automation engine facade."""

from apps.service_desk.services.automation_service import AutomationService

__all__ = ["AutomationService"]


def run_trigger(trigger: str, ticket, **kwargs):
    return AutomationService.dispatch(trigger, ticket=ticket, **kwargs)
