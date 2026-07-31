from django.contrib import admin
from django.urls import path, include


urlpatterns = [

    # Enterprise Service Desk Homepage
    path(
        "",
        include("apps.service_desk.urls")
    ),


    # Admin Console
    path(
        "admin/",
        admin.site.urls
    ),


    # Service Desk Module API/UI namespace
    path(
        "service-desk/",
        include("apps.service_desk.urls")
    ),

]