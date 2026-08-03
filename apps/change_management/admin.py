from django.contrib import admin

from apps.change_management.models import CABMeeting, ChangeApproval, ChangeRequest


class ChangeApprovalInline(admin.TabularInline):
    model = ChangeApproval
    extra = 0


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "change_type",
        "risk",
        "state",
        "cab_required",
        "scheduled_start",
        "company",
    )
    list_filter = ("change_type", "risk", "state", "company")
    search_fields = ("ticket__ticket_number", "justification")
    inlines = [ChangeApprovalInline]
    raw_id_fields = ("ticket", "company", "requester")


@admin.register(CABMeeting)
class CABMeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "scheduled_at", "chair", "is_closed", "company")
    list_filter = ("is_closed", "company")
    filter_horizontal = ("members", "changes")
    search_fields = ("title", "minutes")


@admin.register(ChangeApproval)
class ChangeApprovalAdmin(admin.ModelAdmin):
    list_display = ("change", "approver", "decision", "decided_at")
    list_filter = ("decision",)