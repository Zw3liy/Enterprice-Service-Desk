from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.serializers import ChatbotMessageSerializer
from apps.chatbot.services import ChatbotService
from apps.service_desk.tenancy import require_company


class ChatbotAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChatbotMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        result = ChatbotService.handle(
            user=request.user,
            company=company,
            message=ser.validated_data["message"],
        )
        return Response(result)
