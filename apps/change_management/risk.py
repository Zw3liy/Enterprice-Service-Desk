from apps.change_management.models import ChangeRequest

def risk_choices():
    return list(ChangeRequest.Risk.choices)
