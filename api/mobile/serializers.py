from rest_framework import serializers


class MobileBootstrapSerializer(serializers.Serializer):
    username = serializers.CharField()
    company_name = serializers.CharField(allow_null=True)
