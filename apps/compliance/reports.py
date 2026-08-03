from apps.compliance.services import ComplianceService

def framework_report(framework):
    return ComplianceService.scorecard(framework)
