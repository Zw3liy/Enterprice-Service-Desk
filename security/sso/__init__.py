"""SSO package: OAuth2/OIDC and SAML helpers."""

from security.sso.oauth import OAuth2Client, OAuthProviderConfig
from security.sso.providers import get_provider, list_configured_providers
from security.sso.saml import SAMLIdentity, SAMLValidator, build_demo_assertion

__all__ = [
    "OAuth2Client",
    "OAuthProviderConfig",
    "get_provider",
    "list_configured_providers",
    "SAMLIdentity",
    "SAMLValidator",
    "build_demo_assertion",
]