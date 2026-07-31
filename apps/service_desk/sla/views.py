from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.service_desk.models import SLA
from apps.service_desk.tenancy import get_active_company


@login_required
def sla_list(request):
    company = get_active_company(request)
    qs = SLA.objects.all()
    if company:
        qs = qs.filter(company=company)
    return render(
        request,
        "service_desk/reports/index.html",
        {"title": "SLA policies", "summary": {"open_tickets": qs.count()}, "slas": qs},
    )


@login_required
def sla_home(request):
    return redirect("service_desk:reports")
