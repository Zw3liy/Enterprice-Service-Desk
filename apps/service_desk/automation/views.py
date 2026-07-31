from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def automation_home(request):
    return redirect("service_desk:reports")
