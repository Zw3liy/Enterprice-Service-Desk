from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.workflow.serializers import WorkflowTransitionSerializer
from apps.service_desk.models import Status, Ticket
from apps.service_desk.workflow.engine import WorkflowEngine


class WorkflowTransitionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = WorkflowTransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ticket = get_object_or_404(Ticket, pk=ser.validated_data["ticket_id"])
        status_obj = get_object_or_404(Status, pk=ser.validated_data["status_id"])
        ticket = WorkflowEngine.transition(ticket, status_obj, actor=request.user)
        return Response(
            {
                "ticket_id": ticket.pk,
                "ticket_number": ticket.ticket_number,
                "status": ticket.status.code if ticket.status_id else None,
            }
        )
