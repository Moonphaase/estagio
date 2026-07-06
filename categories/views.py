from rest_framework import viewsets, permissions, filters
from .models import Category
from .serializers import CategorySerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field       = "slug"
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "description"]
    ordering_fields    = ["name", "created_at"]