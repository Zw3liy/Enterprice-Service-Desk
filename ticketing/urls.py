from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentication
    path(
        "accounts/",
        include("django.contrib.auth.urls")
    ),

    # Enterprise Service Desk
    path(
        "",
        include("apps.service_desk.urls")
    ),
]