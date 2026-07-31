from rest_framework import serializers

from apps.network_discovery.models import DiscoveredHost, DiscoveryScan


class DiscoveredHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoveredHost
        fields = (
            "id",
            "scan",
            "company",
            "ip_address",
            "hostname",
            "mac_address",
            "open_ports",
            "os_guess",
            "is_alive",
            "raw",
            "created_at",
        )


class DiscoveryScanSerializer(serializers.ModelSerializer):
    hosts = DiscoveredHostSerializer(many=True, read_only=True)

    class Meta:
        model = DiscoveryScan
        fields = (
            "id",
            "company",
            "name",
            "cidr",
            "state",
            "started_at",
            "finished_at",
            "hosts_found",
            "error_message",
            "created_by",
            "hosts",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "state",
            "started_at",
            "finished_at",
            "hosts_found",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
        )


class DiscoveryScanCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    cidr = serializers.CharField(max_length=64)
    run_immediately = serializers.BooleanField(default=True)
