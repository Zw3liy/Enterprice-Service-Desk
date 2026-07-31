from apps.asset_lifecycle_management.services import AssetLifecycleService
from apps.service_desk.models import Asset


def dispose(asset: Asset, actor=None):
    # ensure retired first when possible
    if asset.lifecycle_state not in {
        Asset.LifecycleState.RETIRED,
        Asset.LifecycleState.DISPOSED,
        Asset.LifecycleState.ORDERED,
        Asset.LifecycleState.IN_STOCK,
    }:
        AssetLifecycleService.retire(asset, actor=actor)
    return AssetLifecycleService.transition(
        asset, Asset.LifecycleState.DISPOSED, actor=actor, notes="Disposed"
    )
