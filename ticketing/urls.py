"""
==============================================================
Enterprise Service Desk
Main URL Configuration
==============================================================
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [

    # ==========================================================
    # Administration
    # ==========================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # ==========================================================
    # Authentication
    # Django built-in login/logout/password management
    # ==========================================================

    path(
        "accounts/",
        include("django.contrib.auth.urls")
    ),


    # ==========================================================
    # Enterprise UI
    # Dashboard, profile, settings, search
    # ==========================================================

    path(
        "",
        include("apps.ui.urls")
    ),


    # ==========================================================
    # Service Desk Core
    # ==========================================================

    path(
        "service-desk/",
        include("apps.service_desk.urls")
    ),

]