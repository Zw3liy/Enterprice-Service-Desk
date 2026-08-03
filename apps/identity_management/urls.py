from django.urls import path

from apps.identity_management import views

app_name = "identity"

urlpatterns = [
    path("sso/", views.sso_index, name="sso"),
    path("sso/oauth/<str:provider>/", views.oauth_start, name="oauth_start"),
    path("sso/oauth/<str:provider>/callback/", views.oauth_callback, name="oauth_callback"),
    path("sso/saml/acs/", views.saml_acs, name="saml_acs"),
]