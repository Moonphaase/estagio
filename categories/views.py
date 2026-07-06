from rest_framework import viewsets, permissions, filters
from .models import Category
from .serializers import CategorySerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Permite leitura para qualquer utilizador autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Permite escrita apenas para admins
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    # Aqui permitimos que o IsAuthenticated global e a nossa classe tratem o acesso
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    lookup_field       = "slug"
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "description"]
    ordering_fields    = ["name", "created_at"]