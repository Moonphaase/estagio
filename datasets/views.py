import logging
import os

from django.db import transaction
from django.db.models import Q, Count
from django.http import FileResponse
from django.utils import timezone
from datetime import timedelta

from core.permissions import IsOwnerOrAdmin, IsAdminOrReadOnly
from core.pagination import StandardPagination
from core.helpers import generate_checksum, validate_file_extension, validate_file_size, dataset_upload_path

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Dataset, DatasetVersion, DownloadLog, DatasetFavorite  # ← DatasetFavorite
from .permissions import IsOwnerOrAdmin
from .serializers import (
    DatasetSerializer, DatasetListSerializer,
    DatasetVersionSerializer, DatasetStatsSerializer,
    DatasetFavoriteSerializer,  # ← novo
)

logger = logging.getLogger('datasets')


def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class DatasetViewSet(viewsets.ModelViewSet):  # ← só UMA definição
    queryset = Dataset.objects.select_related("owner", "category", "metadata")
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["name", "description", "category__name"]
    ordering_fields  = ["name", "created_at", "updated_at", "status", "visibility"]

    def get_serializer_class(self):
        if self.action == "list":
            return DatasetListSerializer
        return DatasetSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_authenticated and user.is_staff:
            pass
        elif user.is_authenticated:
            qs = qs.filter(Q(visibility="public") | Q(owner=user))
        else:
            qs = qs.filter(visibility="public", status="published")

        category   = self.request.query_params.get("category")
        owner      = self.request.query_params.get("owner")
        visibility = self.request.query_params.get("visibility")
        ds_status  = self.request.query_params.get("status")

        if category:
            qs = qs.filter(category__slug=category)
        if owner:
            qs = qs.filter(owner__username=owner)
        if visibility:
            qs = qs.filter(visibility=visibility)
        if ds_status:
            qs = qs.filter(status=ds_status)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        dataset = serializer.save(owner=self.request.user)
        logger.info(f'Dataset criado: "{dataset.name}" por {self.request.user.email}')

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        response = super().update(request, *args, **kwargs)
        logger.info(f'Dataset editado: "{instance.name}" por {request.user.email}')
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        logger.info(f'Dataset apagado: "{instance.name}" por {request.user.email}')
        return super().destroy(request, *args, **kwargs)

    # ── FAVORITOS ────────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        dataset = self.get_object()
        favorite, created = DatasetFavorite.objects.get_or_create(
            user=request.user,
            dataset=dataset
        )
        if not created:
            favorite.delete()
            return Response({'status': 'removed', 'is_favorited': False})
        return Response({'status': 'added', 'is_favorited': True}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_favorites(self, request):
        favorites = DatasetFavorite.objects.filter(
            user=request.user
        ).select_related('dataset')
        serializer = DatasetFavoriteSerializer(favorites, many=True)
        return Response(serializer.data)

    # ── DOWNLOADS ────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="latest/download")
    def latest_download(self, request, pk=None):
        dataset = self.get_object()
        version = dataset.versions.filter(is_latest=True).first()
        if not version:
            return Response({"detail": "Este dataset não tem versões."}, status=status.HTTP_404_NOT_FOUND)
        if not version.file or not os.path.exists(version.file.path):
            return Response({"detail": "Ficheiro não encontrado no servidor."}, status=status.HTTP_404_NOT_FOUND)
        DownloadLog.objects.create(
            dataset=dataset, version=version,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
        )
        logger.info(f'Download latest: "{dataset.name}" v{version.version} por {request.user}')
        response = FileResponse(version.file.open("rb"), as_attachment=True)
        response["Content-Length"] = version.file_size
        return response

    @action(detail=True, methods=["get"], url_path="stats",
            permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def stats(self, request, pk=None):
        dataset = self.get_object()
        now = timezone.now()
        total  = DownloadLog.objects.filter(dataset=dataset).count()
        last_7 = DownloadLog.objects.filter(dataset=dataset, downloaded_at__gte=now - timedelta(days=7)).count()
        last_30 = DownloadLog.objects.filter(dataset=dataset, downloaded_at__gte=now - timedelta(days=30)).count()
        by_version = (
            DownloadLog.objects
            .filter(dataset=dataset, version__isnull=False)
            .values("version__version")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        data = {
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "total_downloads": total,
            "downloads_last_7_days": last_7,
            "downloads_last_30_days": last_30,
            "downloads_by_version": [
                {"version": row["version__version"], "total": row["total"]}
                for row in by_version
            ],
        }
        serializer = DatasetStatsSerializer(data)
        return Response(serializer.data)


class DatasetVersionViewSet(viewsets.ModelViewSet):
    serializer_class   = DatasetVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DatasetVersion.objects.filter(
            dataset_id=self.kwargs["dataset_pk"]
        ).select_related("created_by")

    def get_dataset(self):
        return Dataset.objects.get(pk=self.kwargs["dataset_pk"])

    def perform_create(self, serializer):
        dataset = self.get_dataset()
        if dataset.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("Apenas o dono ou um admin pode criar versões.")
        version_number = serializer.validated_data.get("version")
        with transaction.atomic():
            if dataset.versions.filter(version=version_number).exists():
                raise PermissionDenied(f"A versão '{version_number}' já existe neste dataset.")
            dataset.versions.filter(is_latest=True).update(is_latest=False)
            version = serializer.save(
                dataset=dataset,
                created_by=self.request.user,
                is_latest=True,
            )
            logger.info(f'Versão criada: "{dataset.name}" v{version.version} por {self.request.user.email}')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        dataset  = self.get_dataset()
        if dataset.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("Apenas o dono ou um admin pode apagar versões.")
        was_latest = instance.is_latest
        logger.info(f'Versão apagada: "{dataset.name}" v{instance.version} por {request.user.email}')
        instance.delete()
        if was_latest:
            next_latest = dataset.versions.order_by("-created_at").first()
            if next_latest:
                next_latest.is_latest = True
                next_latest.save(update_fields=["is_latest"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def download(self, request, dataset_pk=None, pk=None):
        version = self.get_object()
        if not version.file:
            return Response({"detail": "Ficheiro não disponível."}, status=status.HTTP_404_NOT_FOUND)
        if not os.path.exists(version.file.path):
            return Response({"detail": "Ficheiro não encontrado no servidor."}, status=status.HTTP_404_NOT_FOUND)
        DownloadLog.objects.create(
            dataset=version.dataset, version=version,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
        )
        logger.info(f'Download: v{version.version} do dataset {version.dataset.name} por {request.user}')
        response = FileResponse(version.file.open("rb"), as_attachment=True)
        response["Content-Length"] = version.file_size
        return response