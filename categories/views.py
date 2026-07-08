from rest_framework import viewsets, permissions, filters
import logging
from api_keys.models import APIKey
from .models import Category
from .serializers import CategorySerializer

# Configuração de logger para visualizar nos logs do Railway
logger = logging.getLogger(__name__)

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Log para verificar quem é o user antes da verificação
        # Isto aparecerá nos logs do Railway/Servidor
        logger.info(f"DEBUG AUTH: User={request.user}, IsAuthenticated={request.user.is_authenticated}")

        # Exige sempre uma API Key válida, independentemente do método
        if not isinstance(request.auth, APIKey):
            return False

        # Se for apenas leitura (GET, HEAD, OPTIONS), a key válida já basta
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Se for escrita, exige adicionalmente que o utilizador seja staff
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminOrReadOnly]

    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    lookup_field       = "slug"
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "description"]
    ordering_fields    = ["name", "created_at"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)