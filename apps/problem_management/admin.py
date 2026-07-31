from django.contrib import admin

from apps.problem_management.models import ProblemRecord


@admin.register(ProblemRecord)
class ProblemRecordAdmin(admin.ModelAdmin):
    list_display = ("ticket", "state", "owner", "company", "created_at")
    list_filter = ("state", "company")
    search_fields = ("ticket__ticket_number", "root_cause")
    filter_horizontal = ("related_incidents",)
    raw_id_fields = ("ticket", "owner", "known_error_article", "company")