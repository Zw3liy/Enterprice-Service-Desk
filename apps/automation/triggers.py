from apps.service_desk.models import AutomationRule


def available_triggers() -> list[tuple[str, str]]:
    return list(AutomationRule.Trigger.choices)
