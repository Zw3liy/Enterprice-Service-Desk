from django.contrib import admin

from apps.network_discovery.models import DiscoveredHost, DiscoveryScan


class DiscoveredHostInline(admin.TabularInline):
    model = DiscoveredHost
    extra = 0
    readonly_fields = ("ip_address", "hostname", "mac_address", "open_ports", "os_guess")


@admin.register(DiscoveryScan)
class DiscoveryScanAdmin(admin.ModelAdmin):
    list_display = ("name", "cidr", "state", "hosts_found", "started_at", "finished_at", "company")
    list_filter = ("state", "company")
    inlines = [DiscoveredHostInline]


@admin.register(DiscoveredHost)
class DiscoveredHostAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "hostname", "scan", "os_guess", "is_alive")
    list_filter = ("is_alive", "company")
    search_fields = ("ip_address", "hostname", "mac_address")
