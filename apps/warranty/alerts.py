from apps.warranty.services import WarrantyService

def expiring_alert_count(company, days=30):
    return WarrantyService.expiring(company, within_days=days).count()
