from django.urls import path

from apps.mfa import views

app_name = "mfa"

urlpatterns = [
    path("setup/", views.mfa_setup, name="setup"),
    path("disable/", views.mfa_disable, name="disable"),
    path("api/status/", views.MFAStatusAPI.as_view(), name="api-status"),
    path("api/enroll/", views.MFAEnrollAPI.as_view(), name="api-enroll"),
    path("api/confirm/", views.MFAConfirmAPI.as_view(), name="api-confirm"),
    path("api/verify/", views.MFAVerifyAPI.as_view(), name="api-verify"),
]