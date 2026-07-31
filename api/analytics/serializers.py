from rest_framework import serializers


class AnalyticsKPISerializer(serializers.Serializer):
    open_tickets = serializers.IntegerField()
    resolved_tickets = serializers.IntegerField()
    breached_tickets = serializers.IntegerField()
    sla_compliance_pct = serializers.FloatField(allow_null=True)
