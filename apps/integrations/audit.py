from apps.service_desk.services.audit_service import AuditService


def log_integration(company, action: str, message: str = "", actor=None, metadata=None):
    return AuditService.log(
        action=f"integration.{action}",
        company=company,
        actor=actor,
        message=message,
        object_type="integration",
        metadata=metadata or {},
    )
