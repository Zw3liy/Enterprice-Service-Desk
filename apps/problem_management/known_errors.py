from apps.problem_management.models import ProblemRecord

def known_errors(company=None):
    qs = ProblemRecord.objects.filter(state=ProblemRecord.State.KNOWN_ERROR)
    if company is not None:
        qs = qs.filter(company=company)
    return qs
