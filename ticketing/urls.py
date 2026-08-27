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
# Production health boundaries.
from django.urls import path as health_path
from ticketing.health_views import liveness, readiness

urlpatterns += [
    health_path("health/live/", liveness, name="health-live"),
    health_path("health/ready/", readiness, name="health-ready"),
]
