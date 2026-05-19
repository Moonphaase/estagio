from rest_framework import serializers
from .models import Dataset, DatasetVersion, DatasetMetadata
import re
 
 
class DatasetMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DatasetMetadata
        fields = ["source", "license", "tags", "language",
                  "size_bytes", "num_records", "extra", "updated_at"]
        read_only_fields = ["updated_at"]
 
 
class DatasetVersionSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    file_url   = serializers.SerializerMethodField()
 
    class Meta:
        model  = DatasetVersion
        fields = [
            "id", "version", "title", "file", "file_url",
            "file_size", "file_type", "checksum",
            "notes", "is_latest", "created_at", "created_by",
        ]
        read_only_fields = [
            "id", "file_size", "file_type", "checksum",
            "is_latest", "created_at", "created_by",
        ]
 
    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
 
    def validate_version(self, value):
        """Validar formato semântico MAJOR.MINOR.PATCH ou MAJOR.MINOR"""
        if not re.match(r"^\d+\.\d+(\.\d+)?$", value):
            raise serializers.ValidationError(
                "O número de versão deve seguir o formato semântico (ex: 1.0.0 ou 1.0)."
            )
        return value
 
 
class DatasetSerializer(serializers.ModelSerializer):
    owner         = serializers.StringRelatedField(read_only=True)
    metadata      = DatasetMetadataSerializer(read_only=True)
    versions      = DatasetVersionSerializer(many=True, read_only=True)
    version_count = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()
 
    class Meta:
        model  = Dataset
        fields = [
            "id", "name", "slug", "description", "category",
            "owner", "visibility", "status", "metadata",
            "versions", "version_count", "latest_version",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]
 
    def get_version_count(self, obj):
        return obj.versions.count()
 
    def get_latest_version(self, obj):
        latest = obj.versions.filter(is_latest=True).first()
        if latest:
            return {"id": latest.id, "version": latest.version}
        return None
 
 
class DatasetListSerializer(serializers.ModelSerializer):
    """Serializer leve para listagens — sem versões completas."""
    owner          = serializers.StringRelatedField(read_only=True)
    category_name  = serializers.CharField(source="category.name", read_only=True)
    version_count  = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()
 
    class Meta:
        model  = Dataset
        fields = [
            "id", "name", "slug", "description",
            "category", "category_name",
            "owner", "visibility", "status",
            "version_count", "latest_version",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]
 
    def get_version_count(self, obj):
        return obj.versions.count()
 
    def get_latest_version(self, obj):
        latest = obj.versions.filter(is_latest=True).first()
        if latest:
            return {"id": latest.id, "version": latest.version}
        return None
 