from django.shortcuts import render


def dashboard(request):
    context = {
        "title": "Enterprise Service Desk",
        "total_tickets": 0,
        "open_tickets": 0,
        "resolved_tickets": 0,
    }

    return render(
        request,
        "service_desk/dashboard.html",
        context
    )