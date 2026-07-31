from rest_framework import serializers

from apps.ai_engine.models import AIConversation, AIMessage, AIRequestLog


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ("id", "role", "content", "metadata", "created_at")


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIConversation
        fields = (
            "id",
            "title",
            "ticket",
            "is_active",
            "messages",
            "created_at",
            "updated_at",
        )


class CopilotAskSerializer(serializers.Serializer):
    message = serializers.CharField()
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    ticket_id = serializers.IntegerField(required=False, allow_null=True)
    provider = serializers.ChoiceField(
        choices=["local", "openai", "claude", "ollama"], default="local", required=False
    )


class AIRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequestLog
        fields = (
            "id",
            "provider",
            "operation",
            "prompt",
            "response",
            "latency_ms",
            "success",
            "error_message",
            "created_at",
        )