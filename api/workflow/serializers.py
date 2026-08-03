from rest_framework import serializers


class WorkflowTransitionSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    status_id = serializers.IntegerField()
