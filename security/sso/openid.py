"""OpenID Connect convenience wrappers."""

from __future__ import annotations

from security.sso.oauth import OAuth2Client, OAuthProviderConfig, azure_ad_config, google_config

__all__ = [
    "OAuth2Client",
    "OAuthProviderConfig",
    "azure_ad_config",
    "google_config",
]