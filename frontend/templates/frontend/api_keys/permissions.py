from rest_framework.permissions import BasePermission
from datasets.models import ApiKey  # ajusta o nome do modelo se for diferente


class HasValidApiKey(BasePermission):
    message = "Acesso requer uma API Key válida."

    def has_permission(self, request, view):
        return isinstance(request.auth, ApiKey)