from django.contrib import admin

from apps.approval_engine.models import ApprovalPolicy


@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "entity_type", "min_approvers", "is_active", "company")
    list_filter = ("entity_type", "is_active", "company")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}
