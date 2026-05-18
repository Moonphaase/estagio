from rest_framework import serializers
from .models import Dataset, DatasetVersion, DatasetMetadata


class DatasetMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DatasetMetadata
        fields = ["source", "license", "tags", "language",
                  "size_bytes", "num_records", "extra", "updated_at"]
        read_only_fields = ["updated_at"]


class DatasetVersionSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = DatasetVersion
        fields = ["id", "version", "file", "notes", "created_at", "created_by"]
        read_only_fields = ["id", "created_at", "created_by"]


class DatasetSerializer(serializers.ModelSerializer):
    owner    = serializers.StringRelatedField(read_only=True)
    metadata = DatasetMetadataSerializer(read_only=True)

    class Meta:
        model  = Dataset
        fields = ["id", "name", "slug", "description", "category",
                  "owner", "visibility", "status", "metadata",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]