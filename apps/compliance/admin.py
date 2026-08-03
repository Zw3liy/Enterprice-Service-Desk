from django.contrib import admin

from apps.compliance.models import ComplianceEvidence, Control, ControlFramework


class ControlInline(admin.TabularInline):
    model = Control
    extra = 0


@admin.register(ControlFramework)
class ControlFrameworkAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "version", "company")
    list_filter = ("company",)
    search_fields = ("name", "code")
    inlines = [ControlInline]


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = ("control_id", "title", "status", "framework", "owner")
    list_filter = ("status", "framework")
    search_fields = ("control_id", "title")


@admin.register(ComplianceEvidence)
class ComplianceEvidenceAdmin(admin.ModelAdmin):
    list_display = ("title", "control", "collected_by", "collected_at")
    search_fields = ("title", "description")
