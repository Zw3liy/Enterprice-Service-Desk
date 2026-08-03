from django.contrib import admin

from apps.form_builder.models import FormDefinition, FormSubmission


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "version", "is_active", "request_type", "company")
    list_filter = ("is_active", "company")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("form", "submitted_by", "ticket", "created_at", "company")
    list_filter = ("company", "form")
    readonly_fields = ("values",)
