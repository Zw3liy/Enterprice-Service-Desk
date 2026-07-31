from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from apps.service_desk.reporting.exports import tickets_csv
from apps.service_desk.tenancy import get_active_company
from apps.service_desk.views import reports_index


@login_required
def export_tickets(request):
    company = get_active_company(request)
    from apps.service_desk.models import Ticket

    qs = Ticket.objects.all()
    if company:
        qs = qs.filter(company=company)
    content = tickets_csv(qs)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tickets.csv"'
    return response


reports_home = reports_index
