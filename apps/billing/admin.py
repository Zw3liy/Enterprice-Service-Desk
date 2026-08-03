from django.contrib import admin

from apps.billing.models import Invoice, Plan, Subscription, UsageRecord


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "tier",
        "price_monthly",
        "max_agents",
        "is_active",
        "sort_order",
    )
    list_filter = ("tier", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "plan", "status", "seats", "trial_ends_at", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("company__name", "billing_email", "external_subscription_id")
    raw_id_fields = ("company", "plan")


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("company", "metric", "quantity", "period_start", "period_end")
    list_filter = ("metric", "company")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "company", "status", "total", "currency", "due_date", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("number", "company__name")
    readonly_fields = ("number",)