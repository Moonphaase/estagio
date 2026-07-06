from rest_framework import viewsets, permissions, filters
from .models import Category
from .serializers import CategorySerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Se for apenas leitura (GET, HEAD, OPTIONS), permite se estiver autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Se for escrita, exige que seja staff
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    # Removemos o IsAuthenticated daqui porque ele já é global no settings.py
    # Assim, só precisamos desta regra de Admin
    permission_classes = [IsAdminOrReadOnly]
    
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    lookup_field       = "slug"
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "description"]
    ordering_fields    = ["name", "created_at"]