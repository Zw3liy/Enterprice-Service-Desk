from django.contrib import admin

from apps.ai_engine.models import AIConversation, AIMessage, AIRequestLog


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "ticket", "is_active", "updated_at")
    list_filter = ("is_active", "company")
    search_fields = ("title", "user__username")
    inlines = [AIMessageInline]


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ("operation", "provider", "success", "latency_ms", "user", "created_at")
    list_filter = ("provider", "success", "operation")
    search_fields = ("prompt", "response", "error_message")
