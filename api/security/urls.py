from django.urls import path

from api.security.siem_views import SIEMExportAPI
from api.security.views import SecurityStatusAPI
from apps.mfa.views import MFAConfirmAPI, MFAEnrollAPI, MFAStatusAPI, MFAVerifyAPI

urlpatterns = [
    path("status/", SecurityStatusAPI.as_view(), name="api-security-status"),
    path("siem/export/", SIEMExportAPI.as_view(), name="api-siem-export"),
    path("mfa/status/", MFAStatusAPI.as_view(), name="api-sec-mfa-status"),
    path("mfa/enroll/", MFAEnrollAPI.as_view(), name="api-sec-mfa-enroll"),
    path("mfa/confirm/", MFAConfirmAPI.as_view(), name="api-sec-mfa-confirm"),
    path("mfa/verify/", MFAVerifyAPI.as_view(), name="api-sec-mfa-verify"),
]
