from django.urls import path

from apps.service_desk.views import ServiceDeskLoginView, ServiceDeskLogoutView, register

urlpatterns = [
    path("login/", ServiceDeskLoginView.as_view(), name="identity_login"),
    path("logout/", ServiceDeskLogoutView.as_view(), name="identity_logout"),
    path("register/", register, name="identity_register"),
]
