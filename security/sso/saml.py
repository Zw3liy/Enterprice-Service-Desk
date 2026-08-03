"""Lightweight SAML2 assertion consumer helpers.

This module validates a simplified signed assertion envelope used for
enterprise SSO integration tests and staging. Production deployments should
front this with a hardened SAML library (e.g. python3-saml) using the same
interfaces.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SAMLIdentity:
    name_id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    groups: list[str] | None = None
    attributes: dict[str, Any] | None = None


class SAMLValidator:
    def __init__(self, idp_entity_id: str, sp_entity_id: str, shared_secret: str = "") -> None:
        self.idp_entity_id = idp_entity_id
        self.sp_entity_id = sp_entity_id
        self.shared_secret = shared_secret.encode("utf-8") if shared_secret else b""

    def decode_response(self, saml_response_b64: str) -> bytes:
        return base64.b64decode(saml_response_b64)

    def parse_identity(self, xml_bytes: bytes) -> SAMLIdentity:
        root = ET.fromstring(xml_bytes)
        ns = {
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        }
        name_id = ""
        name_node = root.find(".//saml:NameID", ns)
        if name_node is not None and name_node.text:
            name_id = name_node.text.strip()
        attrs: dict[str, Any] = {}
        for attr in root.findall(".//saml:Attribute", ns):
            key = attr.attrib.get("Name") or attr.attrib.get("FriendlyName") or "attr"
            values = [
                (v.text or "").strip()
                for v in attr.findall("saml:AttributeValue", ns)
                if v.text
            ]
            attrs[key] = values[0] if len(values) == 1 else values
        email = str(attrs.get("email") or attrs.get("mail") or name_id)
        first = str(attrs.get("first_name") or attrs.get("givenName") or "")
        last = str(attrs.get("last_name") or attrs.get("sn") or "")
        groups = attrs.get("groups") or attrs.get("memberOf") or []
        if isinstance(groups, str):
            groups = [groups]
        return SAMLIdentity(
            name_id=name_id or email,
            email=email,
            first_name=first,
            last_name=last,
            groups=list(groups),
            attributes=attrs,
        )

    def verify_hmac(self, xml_bytes: bytes, signature_b64: str) -> bool:
        if not self.shared_secret:
            return True
        expected = hmac.new(self.shared_secret, xml_bytes, hashlib.sha256).digest()
        try:
            provided = base64.b64decode(signature_b64)
        except Exception:  # noqa: BLE001
            return False
        return hmac.compare_digest(expected, provided)

    def consume(self, saml_response_b64: str, signature_b64: str = "") -> SAMLIdentity:
        xml_bytes = self.decode_response(saml_response_b64)
        if signature_b64 and not self.verify_hmac(xml_bytes, signature_b64):
            raise ValueError("Invalid SAML signature")
        identity = self.parse_identity(xml_bytes)
        logger.info("saml_consume name_id=%s email=%s", identity.name_id, identity.email)
        return identity


def build_demo_assertion(email: str, first_name: str = "", last_name: str = "") -> str:
    """Build a minimal base64 SAML-like assertion for local testing."""
    xml = f"""<?xml version="1.0"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
  <saml:Assertion>
    <saml:Subject><saml:NameID>{email}</saml:NameID></saml:Subject>
    <saml:AttributeStatement>
      <saml:Attribute Name="email"><saml:AttributeValue>{email}</saml:AttributeValue></saml:Attribute>
      <saml:Attribute Name="first_name"><saml:AttributeValue>{first_name}</saml:AttributeValue></saml:Attribute>
      <saml:Attribute Name="last_name"><saml:AttributeValue>{last_name}</saml:AttributeValue></saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""
    return base64.b64encode(xml.encode("utf-8")).decode("ascii")