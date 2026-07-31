from apps.service_desk.workflow.approvals import ApprovalService


def approve(request_obj, actor=None, note: str = ""):
    return ApprovalService.decide(request_obj, approved=True, actor=actor, note=note)


def reject(request_obj, actor=None, note: str = ""):
    return ApprovalService.decide(request_obj, approved=False, actor=actor, note=note)
