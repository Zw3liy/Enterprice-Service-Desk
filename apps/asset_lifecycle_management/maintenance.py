from apps.asset_lifecycle_management.services import AssetLifecycleService
from apps.service_desk.models import Asset


def send_to_maintenance(asset: Asset, actor=None):
    return AssetLifecycleService.transition(
        asset, Asset.LifecycleState.MAINTENANCE, actor=actor, notes="Maintenance"
    )
