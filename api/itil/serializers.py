from rest_framework import serializers


class ITILModuleSerializer(serializers.Serializer):
    name = serializers.CharField()
    path = serializers.CharField()
