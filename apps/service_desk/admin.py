"""Django admin registrations for the Service Desk domain."""

from django.contrib import admin

from apps.service_desk import models as m


class CompanyScopedAdmin(admin.ModelAdmin):
    list_select_related = ("company",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("company")


@admin.register(m.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "timezone", "created_at")
    search_fields = ("name", "slug", "primary_email")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(m.Department)
class DepartmentAdmin(CompanyScopedAdmin):
    list_display = ("name", "code", "company", "ticket_counter", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "code")


@admin.register(m.Contact)
class ContactAdmin(CompanyScopedAdmin):
    list_display = ("full_name", "email", "company", "vip", "is_active")
    list_filter = ("company", "vip", "is_active")
    search_fields = ("first_name", "last_name", "email")


@admin.register(m.AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "company", "is_available", "max_open_tickets")
    list_filter = ("company", "is_available")
    search_fields = ("user__username", "display_name")
    filter_horizontal = ()


@admin.register(m.Category)
class CategoryAdmin(CompanyScopedAdmin):
    list_display = ("name", "code", "company", "parent", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "code")


@admin.register(m.Priority)
class PriorityAdmin(CompanyScopedAdmin):
    list_display = ("name", "code", "rank", "company", "colour", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "code")


@admin.register(m.Status)
class StatusAdmin(CompanyScopedAdmin):
    list_display = ("name", "code", "category", "rank", "is_terminal", "company", "is_active")
    list_filter = ("company", "category", "is_terminal", "is_active")
    search_fields = ("name", "code")


@admin.register(m.Queue)
class QueueAdmin(CompanyScopedAdmin):
    list_display = ("name", "code", "department", "company", "is_active")
    list_filter = ("company", "is_active")
    filter_horizontal = ("members",)
    search_fields = ("name", "code")


class CustomFieldInline(admin.TabularInline):
    model = m.CustomField
    extra = 0


@admin.register(m.RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "is_active")
    list_filter = ("is_active", "department__company")
    search_fields = ("name", "code")
    inlines = [CustomFieldInline]


@admin.register(m.CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "label", "field_type", "request_type", "is_required", "sort_order")
    list_filter = ("field_type", "is_required", "request_type")


@admin.register(m.SLA)
class SLAAdmin(CompanyScopedAdmin):
    list_display = (
        "name",
        "company",
        "priority",
        "response_minutes",
        "resolution_minutes",
        "is_active",
    )
    list_filter = ("company", "is_active")
    search_fields = ("name",)


class EscalationPolicyInline(admin.TabularInline):
    model = m.EscalationPolicy
    extra = 0
    filter_horizontal = ("notify_users",)


@admin.register(m.EscalationPolicy)
class EscalationPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "sla", "level", "trigger_after_percent", "is_active")
    list_filter = ("is_active", "sla__company")
    filter_horizontal = ("notify_users",)


class CommentInline(admin.TabularInline):
    model = m.TicketComment
    extra = 0
    readonly_fields = ("created_at",)


class WorkLogInline(admin.TabularInline):
    model = m.WorkLog
    extra = 0


@admin.register(m.Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "title",
        "ticket_type",
        "status",
        "priority",
        "assignee",
        "company",
        "created_at",
    )
    list_filter = (
        "ticket_type",
        "status",
        "priority",
        "company",
        "is_major_incident",
        "sla_resolution_breached",
    )
    search_fields = ("ticket_number", "title", "description")
    readonly_fields = (
        "ticket_number",
        "uuid",
        "created_at",
        "updated_at",
        "first_response_at",
        "resolved_at",
        "closed_at",
        "response_due_at",
        "resolution_due_at",
        "ai_summary",
        "ai_category_suggestion",
        "sentiment_score",
    )
    autocomplete_fields = (
        "company",
        "department",
        "request_type",
        "category",
        "priority",
        "status",
        "queue",
        "sla",
        "requester",
        "requester_user",
        "assignee",
        "parent",
    )
    filter_horizontal = ("assets", "related_tickets")
    inlines = [CommentInline, WorkLogInline]
    date_hierarchy = "created_at"


@admin.register(m.TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_internal", "is_system", "created_at")
    list_filter = ("is_internal", "is_system")
    search_fields = ("body", "ticket__ticket_number")


@admin.register(m.TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "ticket", "size_bytes", "uploaded_by", "created_at")


@admin.register(m.TicketAssignment)
class TicketAssignmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "assignee", "queue", "assigned_at", "released_at")
    list_filter = ("queue",)


@admin.register(m.WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "minutes_spent", "is_billable", "performed_at")


@admin.register(m.Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ("ticket", "level", "state", "escalated_at", "resolved_at")
    list_filter = ("state", "level")


@admin.register(m.Asset)
class AssetAdmin(CompanyScopedAdmin):
    list_display = (
        "asset_tag",
        "name",
        "asset_type",
        "lifecycle_state",
        "company",
        "is_active",
    )
    list_filter = ("company", "asset_type", "lifecycle_state", "is_active")
    search_fields = ("asset_tag", "name", "serial_number")


@admin.register(m.AssetRelationship)
class AssetRelationshipAdmin(admin.ModelAdmin):
    list_display = ("source", "relation_type", "target")
    list_filter = ("relation_type",)


@admin.register(m.KnowledgeArticle)
class KnowledgeArticleAdmin(CompanyScopedAdmin):
    list_display = (
        "title",
        "company",
        "is_published",
        "is_internal",
        "view_count",
        "published_at",
    )
    list_filter = ("company", "is_published", "is_internal")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(m.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "ticket", "actor", "company", "created_at")
    list_filter = ("action", "company")
    search_fields = ("action", "message", "object_id")
    readonly_fields = [f.name for f in m.AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(m.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("subject", "recipient", "channel", "status", "created_at")
    list_filter = ("channel", "status")


@admin.register(m.WebhookEndpoint)
class WebhookEndpointAdmin(CompanyScopedAdmin):
    list_display = ("name", "url", "company", "is_active")
    list_filter = ("company", "is_active")


@admin.register(m.AutomationRule)
class AutomationRuleAdmin(CompanyScopedAdmin):
    list_display = ("name", "trigger", "priority", "company", "is_active")
    list_filter = ("trigger", "company", "is_active")


@admin.register(m.ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("ticket", "approver", "state", "created_at", "decided_at")
    list_filter = ("state",)


@admin.register(m.CustomerFeedback)
class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = ("ticket", "rating", "submitted_at")
    list_filter = ("rating",)


@admin.register(m.TicketWatcher)
class TicketWatcherAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")
