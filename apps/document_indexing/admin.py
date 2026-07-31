from django.contrib import admin

from apps.document_indexing.models import IndexedDocument


@admin.register(IndexedDocument)
class IndexedDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source_type", "source_id", "is_active", "updated_at", "company")
    list_filter = ("source_type", "is_active", "company")
    search_fields = ("title", "body", "source_id")
