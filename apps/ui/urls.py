"""
==============================================================
Enterprise Service Desk
UI URL Configuration
==============================================================
"""

from django.urls import path
from . import views


app_name = "ui"


urlpatterns = [

    path(
        "",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "profile/",
        views.profile,
        name="profile"
    ),

    path(
        "settings/",
        views.settings,
        name="settings"
    ),

    path(
        "notifications/",
        views.notifications,
        name="notifications"
    ),

    path(
        "search/",
        views.search,
        name="search"
    ),

]