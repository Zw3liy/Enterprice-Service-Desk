from apps.service_desk.services.automation_service import AutomationService

def match(conditions, context):
    return AutomationService._match(conditions or {}, context or {})
