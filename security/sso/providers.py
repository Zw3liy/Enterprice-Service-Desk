"""SSO provider registry loaded from Django settings / env."""

from __future__ import annotations

import os
from typing import Optional

from security.sso.oauth import OAuth2Client, OAuthProviderConfig, azure_ad_config, google_config


def get_provider(name: str, redirect_uri: str) -> Optional[OAuth2Client]:
    name = (name or "").lower().strip()
    if name in {"azure", "azure_ad", "microsoft"}:
        tenant = os.environ.get("AZURE_AD_TENANT_ID", "common")
        client_id = os.environ.get("AZURE_AD_CLIENT_ID", "")
        client_secret = os.environ.get("AZURE_AD_CLIENT_SECRET", "")
        if not client_id:
            return None
        cfg = azure_ad_config(
            tenant_id=tenant,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        return OAuth2Client(cfg)
    if name == "google":
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
        if not client_id:
            return None
        cfg = google_config(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        return OAuth2Client(cfg)
    return None


def list_configured_providers() -> list[str]:
    providers = []
    if os.environ.get("AZURE_AD_CLIENT_ID"):
        providers.append("azure_ad")
    if os.environ.get("GOOGLE_OAUTH_CLIENT_ID"):
        providers.append("google")
    return providers