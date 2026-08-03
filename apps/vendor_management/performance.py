from apps.vendor_management.models import Vendor

def risk_ranked(company):
    return Vendor.objects.filter(company=company, is_active=True).order_by("-risk_rating", "name")
