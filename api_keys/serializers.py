from rest_framework import serializers
from .models import APIKey


class APIKeyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['name', 'permissions', 'expires_at']


class APIKeyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id', 'name', 'key_prefix', 'permissions',
                  'is_active', 'expires_at', 'last_used_at', 'created_at']
        read_only_fields = fields