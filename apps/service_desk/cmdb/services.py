from __future__ import annotations

from apps.service_desk.models import Asset, AssetRelationship


class CMDBService:
    @staticmethod
    def link(source: Asset, target: Asset, relation_type: str = "related", notes: str = ""):
        return AssetRelationship.objects.get_or_create(
            source=source,
            target=target,
            relation_type=relation_type,
            defaults={"notes": notes},
        )[0]

    @staticmethod
    def dependents(asset: Asset):
        return Asset.objects.filter(inbound_relations__source=asset).distinct()
