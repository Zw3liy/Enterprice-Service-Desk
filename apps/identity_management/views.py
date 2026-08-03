"""SSO login endpoints."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.identity_management.services import IdentityService
from apps.service_desk.tenancy import get_active_company
from security.sso import SAMLValidator, build_demo_assertion, get_provider, list_configured_providers

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def sso_index(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "security/sso_login.html",
        {
            "title": "Enterprise SSO",
            "providers": list_configured_providers() or ["azure_ad", "google", "saml_demo"],
        },
    )


@require_http_methods(["GET"])
def oauth_start(request: HttpRequest, provider: str) -> HttpResponse:
    redirect_uri = request.build_absolute_uri(reverse("identity:oauth_callback", args=[provider]))
    client = get_provider(provider, redirect_uri)
    if client is None:
        messages.error(request, f"Provider {provider} is not configured.")
        return redirect("identity:sso")
    state = client.make_state()
    verifier, challenge = client.make_pkce_pair()
    request.session["oauth_state"] = state
    request.session["oauth_verifier"] = verifier
    request.session["oauth_provider"] = provider
    return redirect(client.authorization_url(state, code_challenge=challenge))


@require_http_methods(["GET"])
def oauth_callback(request: HttpRequest, provider: str) -> HttpResponse:
    state = request.GET.get("state")
    code = request.GET.get("code")
    if not code or state != request.session.get("oauth_state"):
        return HttpResponseBadRequest("Invalid OAuth state")
    redirect_uri = request.build_absolute_uri(reverse("identity:oauth_callback", args=[provider]))
    client = get_provider(provider, redirect_uri)
    if client is None:
        return HttpResponseBadRequest("Provider not configured")
    try:
        token = client.exchange_code(code, code_verifier=request.session.get("oauth_verifier"))
        info = client.fetch_userinfo(token.get("access_token", ""))
    except Exception as exc:  # noqa: BLE001
        logger.exception("oauth_callback_failed")
        messages.error(request, f"SSO failed: {exc}")
        return redirect("login")
    email = info.get("email") or info.get("preferred_username") or ""
    if not email:
        messages.error(request, "SSO provider did not return an email.")
        return redirect("login")
    company = get_active_company(request)
    user = IdentityService.upsert_from_sso(
        email=email,
        username=info.get("preferred_username") or email.split("@")[0],
        first_name=info.get("given_name") or info.get("name", "").split(" ")[0],
        last_name=info.get("family_name") or "",
        company=company,
        is_staff=True,
    )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, f"Signed in via {provider}.")
    return redirect("service_desk:dashboard")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def saml_acs(request: HttpRequest) -> HttpResponse:
    """Assertion Consumer Service."""
    if request.method == "GET":
        # Demo mode: mint assertion for local testing
        email = request.GET.get("email") or "sso.user@example.com"
        assertion = build_demo_assertion(email, first_name="SSO", last_name="User")
        identity = SAMLValidator("https://idp.example", "https://esd.example").consume(assertion)
    else:
        response_b64 = request.POST.get("SAMLResponse") or ""
        signature = request.POST.get("Signature") or ""
        if not response_b64:
            return HttpResponseBadRequest("Missing SAMLResponse")
        validator = SAMLValidator(
            idp_entity_id=request.POST.get("Issuer") or "https://idp.example",
            sp_entity_id=request.build_absolute_uri("/"),
            shared_secret=request.POST.get("shared_secret") or "",
        )
        identity = validator.consume(response_b64, signature)
    company = get_active_company(request)
    user = IdentityService.upsert_from_sso(
        email=identity.email,
        username=identity.name_id.split("@")[0],
        first_name=identity.first_name,
        last_name=identity.last_name,
        company=company,
        is_staff=True,
        groups=identity.groups,
    )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Signed in via SAML.")
    return redirect("service_desk:dashboard")