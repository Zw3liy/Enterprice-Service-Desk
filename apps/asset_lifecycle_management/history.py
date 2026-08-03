from apps.service_desk.models import AuditLog


def asset_history(asset):
    return AuditLog.objects.filter(object_type="asset", object_id=str(asset.pk)).order_by(
        "-created_at"
    )
