from rest_framework import serializers

from apps.document_indexing.models import IndexedDocument


class IndexedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndexedDocument
        fields = (
            "id",
            "company",
            "source_type",
            "source_id",
            "title",
            "body",
            "url",
            "tokens",
            "metadata",
            "is_active",
            "updated_at",
        )


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField()
    limit = serializers.IntegerField(required=False, default=25, min_value=1, max_value=100)
