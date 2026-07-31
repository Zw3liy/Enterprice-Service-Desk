from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.agents.copilot import CopilotAgent
from apps.ai_engine.models import AIConversation
from apps.ai_engine.serializers import (
    AIConversationSerializer,
    AIRequestLogSerializer,
    CopilotAskSerializer,
)
from apps.ai_engine.models import AIRequestLog
from apps.service_desk.models import Ticket
from apps.service_desk.services.ai_service import AIService
from apps.service_desk.tenancy import get_active_company


@login_required
@require_http_methods(["GET", "POST"])
def assistant(request):
    company = get_active_company(request)
    answer = None
    classification = None
    articles = []
    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        if message:
            result = CopilotAgent(provider_name=request.POST.get("provider") or "local").reply(
                user=request.user,
                message=message,
                company=company,
            )
            answer = result["answer"]
            classification = result["classification"]
            articles = result["articles"]
    history = AIConversation.objects.filter(user=request.user).order_by("-updated_at")[:10]
    return render(
        request,
        "ai/assistant.html",
        {
            "title": "AI Assistant",
            "answer": answer,
            "classification": classification,
            "articles": articles,
            "history": history,
        },
    )


class CopilotAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CopilotAskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = get_active_company(request)
        ticket = None
        if ser.validated_data.get("ticket_id"):
            ticket = get_object_or_404(Ticket, pk=ser.validated_data["ticket_id"])
        conversation = None
        if ser.validated_data.get("conversation_id"):
            conversation = get_object_or_404(
                AIConversation,
                pk=ser.validated_data["conversation_id"],
                user=request.user,
            )
        result = CopilotAgent(
            provider_name=ser.validated_data.get("provider") or "local"
        ).reply(
            user=request.user,
            message=ser.validated_data["message"],
            company=company,
            ticket=ticket,
            conversation=conversation,
        )
        return Response(result, status=status.HTTP_200_OK)


class ClassifyAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get("text") or ""
        return Response(AIService.classify_text(text))


class ConversationDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        conversation = get_object_or_404(AIConversation, pk=pk, user=request.user)
        return Response(AIConversationSerializer(conversation).data)


class AIRequestLogAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AIRequestLog.objects.filter(user=request.user)[:50]
        if request.user.is_staff:
            company = get_active_company(request)
            qs = AIRequestLog.objects.all()
            if company:
                qs = qs.filter(company=company)
            qs = qs[:100]
        return Response(AIRequestLogSerializer(qs, many=True).data)