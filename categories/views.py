from rest_framework import viewsets, permissions, filters
from .models import Category
from .serializers import CategorySerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permite leitura a todos (ou apenas autenticados) e escrita apenas a admins.
    """
    def has_permission(self, request, view):
        # Se for um método de leitura (GET, HEAD, OPTIONS), verifica se está autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Se for escrita (POST, PUT, DELETE), verifica se é admin
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    # Definimos apenas UMA lista de permissões que exige autenticação
    permission_classes = [IsAdminOrReadOnly]
    
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    lookup_field       = "slug"
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "description"]
    ordering_fields    = ["name", "created_at"]