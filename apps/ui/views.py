from django.shortcuts import render
from django.contrib.auth.models import User


def dashboard(request):

    context = {

        "open_tickets": 0,

        "closed_today": 0,

        "sla_percentage": 100,

        "active_users": User.objects.count(),

    }


    return render(
        request,
        "dashboard/dashboard.html",
        context
    )
from django.shortcuts import render


def profile(request):

    return render(
        request,
        "profile.html"
    )
def settings(request):

    return render(
        request,
        "settings.html"
    )
def notifications(request):

    return render(
        request,
        "notifications.html"
    )


def help_center(request):

    return render(
        request,
        "help.html"
    )
def search(request):

    query = request.GET.get("q", "")

    context = {

        "query": query,

        "results": []

    }


    return render(
        request,
        "search.html",
        context
    )