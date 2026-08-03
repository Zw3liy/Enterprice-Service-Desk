from apps.asset_lifecycle_management.services import AssetLifecycleService


def procure_asset(company, **kwargs):
    return AssetLifecycleService.procure(company, **kwargs)
