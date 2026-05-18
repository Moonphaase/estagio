from django.http import FileResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Dataset, DatasetVersion
from .serializers import DatasetSerializer, DatasetVersionSerializer


class DatasetViewSet(viewsets.ModelViewSet):
    """
    /api/datasets/
    /api/datasets/{id}/
    """
    queryset         = Dataset.objects.select_related("owner", "category", "metadata")
    serializer_class = DatasetSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            # mostra públicos + os próprios
            from django.db.models import Q
            return qs.filter(
                Q(visibility="public") | Q(owner=user)
            )
        return qs.filter(visibility="public")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DatasetVersionViewSet(viewsets.ModelViewSet):
    """
    /api/datasets/{dataset_pk}/versions/
    /api/datasets/{dataset_pk}/versions/{id}/
    /api/datasets/{dataset_pk}/versions/{id}/download/
    """
    serializer_class   = DatasetVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DatasetVersion.objects.filter(
            dataset_id=self.kwargs["dataset_pk"]
        )

    def perform_create(self, serializer):
        dataset = Dataset.objects.get(pk=self.kwargs["dataset_pk"])
        serializer.save(dataset=dataset, created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def download(self, request, dataset_pk=None, pk=None):
        """GET /api/datasets/{dataset_pk}/versions/{id}/download/"""
        version = self.get_object()
        if not version.file:
            return Response(
                {"detail": "Ficheiro não disponível."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(version.file.open("rb"), as_attachment=True)