import hashlib
import os
 
from django.conf import settings
from django.db import models
from django.utils.text import slugify
 
from categories.models import Category
 
ALLOWED_EXTENSIONS = [".csv", ".json", ".xlsx", ".parquet", ".zip"]
 
 
def validate_file_extension(value):
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Extensão não permitida. Aceites: {', '.join(ALLOWED_EXTENSIONS)}"
        )
 
 
def validate_file_size(value):
    from django.core.exceptions import ValidationError
    max_size = 500 * 1024 * 1024  # 500 MB
    if value.size > max_size:
        raise ValidationError("O ficheiro não pode exceder 500 MB.")
 
 
def dataset_version_upload_path(instance, filename):
    """Guarda em media/datasets/{dataset_id}/{version}/filename"""
    safe_name = os.path.basename(filename)
    return f"datasets/{instance.dataset.id}/{instance.version}/{safe_name}"
 
 
class Dataset(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC   = "public",   "Público"
        PRIVATE  = "private",  "Privado"
        INTERNAL = "internal", "Interno"
 
    class Status(models.TextChoices):
        DRAFT     = "draft",     "Rascunho"
        PUBLISHED = "published", "Publicado"
        ARCHIVED  = "archived",  "Arquivado"
 
    # ── campos originais ──────────────────────────────────────────────────────
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="datasets"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
 
    # ── campos novos ──────────────────────────────────────────────────────────
    slug       = models.SlugField(max_length=255, unique=True, blank=True)
    owner      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="datasets"
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    status     = models.CharField(
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
            # Garantir unicidade do slug
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
    version    = models.CharField(max_length=50)           # ex: "1.0.0"
    title      = models.CharField(max_length=255, blank=True)
    file       = models.FileField(
        upload_to=dataset_version_upload_path,
        validators=[validate_file_extension, validate_file_size],
    )
    notes      = models.TextField(blank=True)              # release notes
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="dataset_versions"
    )
 
    # ── campos novos ──────────────────────────────────────────────────────────
    is_latest  = models.BooleanField(default=False)
    file_size  = models.PositiveBigIntegerField(default=0)
    file_type  = models.CharField(max_length=20, blank=True)  # ex: "csv"
    checksum   = models.CharField(max_length=64, blank=True)  # SHA-256
 
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
        # Preencher metadados do ficheiro automaticamente na criação
        if self.file and not self.checksum:
            self.file_size = self.file.size
            self.file_type = os.path.splitext(self.file.name)[1].lower().lstrip(".")
            sha256 = hashlib.sha256()
            for chunk in self.file.chunks():
                sha256.update(chunk)
            self.checksum = sha256.hexdigest()
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.dataset.name} — v{self.version}"
 
 
class DatasetMetadata(models.Model):
    dataset     = models.OneToOneField(
        Dataset, on_delete=models.CASCADE, related_name="metadata"
    )
    source      = models.URLField(blank=True)              # URL de origem
    license     = models.CharField(max_length=100, blank=True)  # ex: "CC BY 4.0"
    tags        = models.JSONField(default=list, blank=True)
    language    = models.CharField(max_length=50, blank=True)
    size_bytes  = models.BigIntegerField(null=True, blank=True)
    num_records = models.PositiveIntegerField(null=True, blank=True)
    extra       = models.JSONField(default=dict, blank=True)   # campo livre
    updated_at  = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name = "Metadados do Dataset"
 
    def __str__(self):
        return f"Metadados — {self.dataset.name}"
 