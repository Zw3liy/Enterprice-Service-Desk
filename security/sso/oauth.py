"""OAuth2 / OIDC authorization-code helpers (provider-agnostic)."""

from __future__ import annotations

import hashlib
import logging
import secrets
import urllib.parse
import urllib.request
import json
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OAuthProviderConfig:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]
    redirect_uri: str


class OAuth2Client:
    def __init__(self, config: OAuthProviderConfig) -> None:
        self.config = config

    def make_state(self) -> str:
        return secrets.token_urlsafe(24)

    def make_pkce_pair(self) -> tuple[str, str]:
        verifier = secrets.token_urlsafe(48)
        challenge = (
            hashlib.sha256(verifier.encode("utf-8")).digest()
        )
        import base64

        challenge_b64 = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")
        return verifier, challenge_b64

    def authorization_url(self, state: str, code_challenge: str | None = None) -> str:
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return f"{self.config.authorize_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str | None = None) -> dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            self.config.token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    def fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        req = urllib.request.Request(
            self.config.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))


def azure_ad_config(
    *,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OAuthProviderConfig:
    base = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0"
    return OAuthProviderConfig(
        name="azure_ad",
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=f"{base}/authorize",
        token_url=f"{base}/token",
        userinfo_url="https://graph.microsoft.com/oidc/userinfo",
        scopes=["openid", "profile", "email", "User.Read"],
        redirect_uri=redirect_uri,
    )


def google_config(
    *, client_id: str, client_secret: str, redirect_uri: str
) -> OAuthProviderConfig:
    return OAuthProviderConfig(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scopes=["openid", "email", "profile"],
        redirect_uri=redirect_uri,
    )