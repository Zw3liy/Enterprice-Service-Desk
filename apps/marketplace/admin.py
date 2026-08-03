from django.contrib import admin

from apps.marketplace.models import InstalledApp, MarketplaceApp


@admin.register(MarketplaceApp)
class MarketplaceAppAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "vendor", "category", "version", "is_published", "is_premium")
    list_filter = ("category", "is_published", "is_premium")
    search_fields = ("name", "slug", "vendor")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(InstalledApp)
class InstalledAppAdmin(admin.ModelAdmin):
    list_display = ("app", "company", "state", "installed_by", "last_sync_at")
    list_filter = ("state", "company")
    raw_id_fields = ("company", "app", "installed_by")
