from rest_framework import serializers


class ForecastQuerySerializer(serializers.Serializer):
    history_days = serializers.IntegerField(required=False, default=28, min_value=7, max_value=120)
    horizon_days = serializers.IntegerField(required=False, default=7, min_value=1, max_value=30)
