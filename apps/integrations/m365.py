"""Microsoft 365 Graph API client (mail/users subset)."""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class M365GraphClient:
    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self.tenant_id = tenant_id or os.environ.get("AZURE_AD_TENANT_ID", "")
        self.client_id = client_id or os.environ.get("AZURE_AD_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("AZURE_AD_CLIENT_SECRET", "")
        self._token: str | None = None

    def acquire_token(self) -> str:
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise RuntimeError("Azure AD app credentials are not configured")
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        self._token = payload["access_token"]
        return self._token

    def _headers(self) -> dict[str, str]:
        token = self._token or self.acquire_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def get(self, path: str) -> dict[str, Any]:
        url = path if path.startswith("http") else f"https://graph.microsoft.com/v1.0{path}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    def list_users(self, top: int = 50) -> list[dict[str, Any]]:
        data = self.get(f"/users?$top={top}&$select=id,displayName,mail,userPrincipalName,jobTitle,department")
        return data.get("value") or []

    def send_mail(self, sender_upn: str, to: list[str], subject: str, body: str) -> None:
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
            },
            "saveToSentItems": True,
        }
        url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(sender_upn)}/sendMail"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            logger.info("m365_send_mail status=%s", getattr(resp, "status", 202))
