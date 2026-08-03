"""Asset lifecycle transitions on core Asset model."""

from __future__ import annotations

import logging

from django.utils import timezone

from apps.service_desk.models import Asset
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AssetLifecycleService:
    ALLOWED = {
        Asset.LifecycleState.ORDERED: {
            Asset.LifecycleState.IN_STOCK,
            Asset.LifecycleState.DISPOSED,
        },
        Asset.LifecycleState.IN_STOCK: {
            Asset.LifecycleState.IN_USE,
            Asset.LifecycleState.DISPOSED,
        },
        Asset.LifecycleState.IN_USE: {
            Asset.LifecycleState.MAINTENANCE,
            Asset.LifecycleState.RETIRED,
            Asset.LifecycleState.IN_STOCK,
        },
        Asset.LifecycleState.MAINTENANCE: {
            Asset.LifecycleState.IN_USE,
            Asset.LifecycleState.RETIRED,
        },
        Asset.LifecycleState.RETIRED: {Asset.LifecycleState.DISPOSED},
        Asset.LifecycleState.DISPOSED: set(),
    }

    @classmethod
    def transition(cls, asset: Asset, new_state: str, *, actor=None, notes: str = "") -> Asset:
        current = asset.lifecycle_state
        allowed = cls.ALLOWED.get(current, set())
        if new_state != current and new_state not in allowed:
            raise ValueError(f"Illegal lifecycle transition {current} → {new_state}")
        asset.lifecycle_state = new_state
        if new_state == Asset.LifecycleState.DISPOSED:
            asset.is_active = False
        if notes:
            asset.notes = (asset.notes + "\n" if asset.notes else "") + (
                f"[{timezone.now().date()}] {notes}"
            )
        asset.save()
        AuditService.log(
            action="asset.lifecycle",
            company=asset.company,
            actor=actor,
            message=f"{asset.asset_tag}: {current} → {new_state}",
            object_type="asset",
            object_id=str(asset.pk),
            metadata={"from": current, "to": new_state},
        )
        logger.info("asset_lifecycle asset=%s %s->%s", asset.asset_tag, current, new_state)
        return asset

    @staticmethod
    def procure(company, *, name: str, asset_tag: str, asset_type: str = Asset.AssetType.OTHER, **kwargs) -> Asset:
        return Asset.objects.create(
            company=company,
            name=name,
            asset_tag=asset_tag,
            asset_type=asset_type,
            lifecycle_state=Asset.LifecycleState.ORDERED,
            **kwargs,
        )

    @staticmethod
    def receive(asset: Asset, actor=None) -> Asset:
        return AssetLifecycleService.transition(
            asset, Asset.LifecycleState.IN_STOCK, actor=actor, notes="Received into stock"
        )

    @staticmethod
    def assign_to_use(asset: Asset, actor=None) -> Asset:
        return AssetLifecycleService.transition(
            asset, Asset.LifecycleState.IN_USE, actor=actor, notes="Deployed to production use"
        )

    @staticmethod
    def retire(asset: Asset, actor=None) -> Asset:
        return AssetLifecycleService.transition(
            asset, Asset.LifecycleState.RETIRED, actor=actor, notes="Retired"
        )
