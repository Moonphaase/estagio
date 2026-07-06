import os
import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from categories.models import Category
from core.helpers import validate_file_extension, validate_file_size, generate_checksum

ALLOWED_EXTENSIONS = [".csv", ".json", ".xlsx", ".parquet", ".zip"]

def dataset_version_upload_path(instance, filename):
    safe_name = os.path.basename(filename)
    return f"datasets/{instance.dataset.id}/{instance.version}/{safe_name}"

# --- MODELO PARA API KEYS ---

class ApiKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dataset_api_keys")
    name = models.CharField(max_length=100)
    key_full = models.CharField(max_length=128) # Guardar a chave completa aqui
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField() # Nova data de expiração
    is_active = models.BooleanField(default=True) # Para controlar o estado

    def save(self, *args, **kwargs):
        # Verifica se a chave expirou antes de salvar
        if self.expires_at < timezone.now():
            self.is_active = False
        super().save(*args, **kwargs)

# --- MODELOS DE DATASETS ---

class Dataset(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC   = "public",   "Público"
        PRIVATE  = "private",  "Privado"
        INTERNAL = "internal", "Interno"

    class Status(models.TextChoices):
        DRAFT     = "draft",    "Rascunho"
        PENDING   = "pending",  "Pendente"
        PUBLISHED = "published", "Publicado"
        ARCHIVED  = "archived",  "Arquivado"

    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="datasets"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    slug        = models.SlugField(max_length=255, unique=True, blank=True)
    owner       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="datasets"
    )
    visibility  = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    status      = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["category"]),
            models.Index(fields=["visibility"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Dataset.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class DatasetVersion(models.Model):
    dataset    = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="versions"
    )
    version    = models.CharField(max_length=50)
    title      = models.CharField(max_length=255, blank=True)
    file       = models.FileField(
        upload_to=dataset_version_upload_path,
        validators=[validate_file_extension, validate_file_size],
    )
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="dataset_versions"
    )
    is_latest  = models.BooleanField(default=False)
    file_size  = models.PositiveBigIntegerField(default=0)
    file_type  = models.CharField(max_length=20, blank=True)
    checksum   = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = "Versão do Dataset"
        verbose_name_plural = "Versões do Dataset"
        ordering = ["-created_at"]
        unique_together = [("dataset", "version")]
        indexes = [
            models.Index(fields=["dataset"]),
            models.Index(fields=["is_latest"]),
        ]

    def save(self, *args, **kwargs):
        if self.file and not self.checksum:
            self.file_size = self.file.size
            self.file_type = os.path.splitext(self.file.name)[1].lower().lstrip(".")
            self.checksum = generate_checksum(self.file)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dataset.name} - v{self.version}"

class DatasetMetadata(models.Model):
    dataset     = models.OneToOneField(
        Dataset, on_delete=models.CASCADE, related_name="metadata"
    )
    source      = models.URLField(blank=True)
    license     = models.CharField(max_length=100, blank=True)
    tags        = models.JSONField(default=list, blank=True)
    language    = models.CharField(max_length=50, blank=True)
    size_bytes  = models.BigIntegerField(null=True, blank=True)
    num_records = models.PositiveIntegerField(null=True, blank=True)
    extra       = models.JSONField(default=dict, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Metadados do Dataset"

    def __str__(self):
        return f"Metadados - {self.dataset.name}"

class Comment(models.Model):
    dataset    = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="comments"
    )
    author     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="comments"
    )
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comentário de {self.author} em {self.dataset.name}"

class DownloadLog(models.Model):
    dataset       = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="download_logs"
    )
    version       = models.ForeignKey(
        DatasetVersion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="download_logs"
    )
    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="download_logs"
    )
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address    = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Log de Download"
        verbose_name_plural = "Logs de Downloads"
        ordering = ["-downloaded_at"]
        indexes = [
            models.Index(fields=["dataset"]),
            models.Index(fields=["downloaded_at"]),
        ]

    def __str__(self):
        return f"Download de {self.dataset.name} em {self.downloaded_at:%Y-%m-%d %H:%M}"

class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Criacao"
        UPDATE = "update", "Edicao"
        DELETE = "delete", "Eliminacao"

    class Resource(models.TextChoices):
        DATASET  = "dataset",  "Dataset"
        VERSION  = "version",  "Versao"
        CATEGORY = "category", "Categoria"
        USER     = "user",     "Utilizador"

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs"
    )
    action        = models.CharField(max_length=10, choices=Action.choices)
    resource      = models.CharField(max_length=10, choices=Resource.choices)
    resource_id   = models.PositiveIntegerField(null=True, blank=True)
    description   = models.TextField(blank=True)
    changes       = models.JSONField(default=dict, blank=True)
    ip_address    = models.GenericIPAddressField(null=True, blank=True)
    timestamp     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["resource", "resource_id"]),
            models.Index(fields=["user"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} - {self.get_action_display()} {self.get_resource_display()} #{self.resource_id}"

class DatasetShare(models.Model):
    dataset     = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="shares"
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="shared_datasets"
    )
    shared_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="dataset_shares_made"
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Partilha de Dataset"
        verbose_name_plural = "Partilhas de Dataset"
        unique_together = [("dataset", "shared_with")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.dataset.name} partilhado com {self.shared_with}"

class DatasetFavorite(models.Model):
    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='favorites'
    )
    dataset   = models.ForeignKey(
        Dataset, on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "dataset")]

    def __str__(self):
        return f"{self.user} ♥ {self.dataset.name}"