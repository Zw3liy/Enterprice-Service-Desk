from apps.service_desk.services.assignment_service import AssignmentService


def least_loaded(ticket, assigned_by=None):
    return AssignmentService.auto_assign(ticket, assigned_by=assigned_by)
