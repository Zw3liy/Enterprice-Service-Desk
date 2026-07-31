"""CMDB application services."""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from apps.cmdb.models import CIClass, CIRelationship, ConfigurationItem, DiscoveryResult
from apps.service_desk.models import Asset, Company
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class CMDBService:
    @staticmethod
    def ensure_default_classes(company: Company) -> None:
        defaults = [
            ("server", "Server", "fa-server"),
            ("application", "Application", "fa-cube"),
            ("database", "Database", "fa-database"),
            ("network", "Network device", "fa-network-wired"),
            ("endpoint", "Endpoint", "fa-laptop"),
            ("service", "Business service", "fa-sitemap"),
        ]
        for code, name, icon in defaults:
            CIClass.objects.get_or_create(
                company=company, code=code, defaults={"name": name, "icon": icon}
            )

    @classmethod
    @transaction.atomic
    def upsert_ci(
        cls,
        company: Company,
        *,
        name: str,
        ci_id: str = "",
        ci_class_code: str = "server",
        asset: Optional[Asset] = None,
        environment: str = "production",
        criticality: int = 3,
        attributes: Optional[dict] = None,
    ) -> ConfigurationItem:
        cls.ensure_default_classes(company)
        ci_class = CIClass.objects.filter(company=company, code=ci_class_code).first()
        if not ci_id:
            base = slugify(name)[:40] or "ci"
            ci_id = f"{ci_class_code.upper()}-{base.upper()}"
        ci, created = ConfigurationItem.objects.update_or_create(
            company=company,
            ci_id=ci_id,
            defaults={
                "name": name,
                "ci_class": ci_class,
                "asset": asset,
                "environment": environment,
                "criticality": criticality,
                "attributes": attributes or {},
                "is_active": True,
            },
        )
        AuditService.log(
            action="cmdb.ci_upsert",
            company=company,
            message=f"{'Created' if created else 'Updated'} CI {ci.ci_id}",
            object_type="configuration_item",
            object_id=str(ci.pk),
            metadata={"ci_id": ci.ci_id},
        )
        return ci

    @staticmethod
    def link(
        source: ConfigurationItem,
        target: ConfigurationItem,
        relation_type: str = CIRelationship.RelationType.RELATED,
        notes: str = "",
    ) -> CIRelationship:
        rel, _ = CIRelationship.objects.get_or_create(
            source=source,
            target=target,
            relation_type=relation_type,
            defaults={"notes": notes},
        )
        return rel

    @staticmethod
    def impact_tree(ci: ConfigurationItem, depth: int = 3) -> dict:
        """Return upstream/downstream dependency snapshot."""

        def walk(node: ConfigurationItem, remaining: int, direction: str):
            if remaining <= 0:
                return []
            rels = (
                node.outbound.select_related("target")
                if direction == "down"
                else node.inbound.select_related("source")
            )
            children = []
            for rel in rels.all():
                child = rel.target if direction == "down" else rel.source
                children.append(
                    {
                        "ci_id": child.ci_id,
                        "name": child.name,
                        "relation": rel.relation_type,
                        "children": walk(child, remaining - 1, direction),
                    }
                )
            return children

        return {
            "ci_id": ci.ci_id,
            "name": ci.name,
            "downstream": walk(ci, depth, "down"),
            "upstream": walk(ci, depth, "up"),
        }

    @staticmethod
    def search(company: Company, query: str = ""):
        qs = ConfigurationItem.objects.filter(company=company, is_active=True).select_related(
            "ci_class", "asset"
        )
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(ci_id__icontains=query)
                | Q(environment__icontains=query)
            )
        return qs

    @classmethod
    def ingest_discovery(cls, company: Company, payload: dict, source: str = "api") -> DiscoveryResult:
        result = DiscoveryResult.objects.create(
            company=company,
            source=source,
            hostname=payload.get("hostname") or "",
            ip_address=payload.get("ip_address"),
            mac_address=payload.get("mac_address") or "",
            os_name=payload.get("os_name") or "",
            raw=payload,
        )
        name = result.hostname or result.ip_address or f"discovered-{result.pk}"
        ci = cls.upsert_ci(
            company,
            name=str(name),
            ci_id=slugify(str(name))[:80].upper() or f"DISC-{result.pk}",
            ci_class_code="server" if "server" in (result.os_name or "").lower() else "endpoint",
            attributes={
                "ip": result.ip_address,
                "mac": result.mac_address,
                "os": result.os_name,
                "source": source,
            },
        )
        result.matched_ci = ci
        result.processed = True
        result.save(update_fields=["matched_ci", "processed", "updated_at"])
        return result

    @staticmethod
    def from_asset(asset: Asset) -> ConfigurationItem:
        return CMDBService.upsert_ci(
            asset.company,
            name=asset.name,
            ci_id=asset.asset_tag,
            ci_class_code={
                Asset.AssetType.SERVER: "server",
                Asset.AssetType.NETWORK_DEVICE: "network",
                Asset.AssetType.COMPUTER: "endpoint",
                Asset.AssetType.SOFTWARE: "application",
            }.get(asset.asset_type, "server"),
            asset=asset,
            attributes={"serial": asset.serial_number, "location": asset.location},
        )