from rest_framework.permissions import BasePermission
from api_keys.models import APIKey


class HasValidApiKey(BasePermission):
    message = "Acesso requer uma API Key válida."

    def has_permission(self, request, view):
        return isinstance(request.auth, APIKey)